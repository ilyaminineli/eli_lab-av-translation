from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import VIDEO_DECK_IDS
from core.audio_analysis import AudioAnalysisFrame, AudioAnalysisSettings
from core.audio_capture import AudioCaptureService
from core.automation import AutomationDirector, AutomationSettings
from core.composition import Composition, Layer
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.modulation import TARGET_SPECS, ModulationMatrix
from core.osc_protocol import OSCReceiver
from core.performance_control import ControlEvent, ControlEventQueue, PerformanceControlState
from core.performance_manager import PerformanceManager
from core.performance_transport import InternalTransport, Quantization
from core.project_manager import ProjectManager
from core.scene_profiles import SceneProfile, SceneProfileRegistry
from effects.settings import EffectSettings
from generators.catalog import GENERATOR_TYPES, default_generator_settings, normalize_settings
from generators.palettes import palette_look
from media.asset_index import VisualAssetIndex
from media.frame_queue import FrameSnapshot
from media.image_overlay import ImageOverlayPlayer
from media.library import MediaLibrary
from media.scanner import SUPPORTED_VIDEO_EXTENSIONS
from media.video_deck import VideoDeck

_LOG = logging.getLogger(__name__)


class Application:
    """Coordinates application services without depending on Qt widgets."""

    def __init__(self) -> None:
        self.events = EventBus()
        self.control_events = ControlEventQueue()
        self.osc_receiver = OSCReceiver(self.submit_control_event)
        self.performance_control = PerformanceControlState()
        self.transport = InternalTransport()
        self._external_clock_bar_at: float | None = None
        self.scene_profiles = SceneProfileRegistry()
        self.modulation = ModulationMatrix()
        self.audio_capture = AudioCaptureService()
        self._audio_sources: dict[str, float] = {}
        self._latest_audio_frame: AudioAnalysisFrame | None = None
        self._selected_layer_id: str | None = None
        self._modulation_base_values: dict[str, float] = {}
        self._animation_started_at = time.perf_counter()
        self.project_manager = ProjectManager()
        self.media_library = MediaLibrary()
        resource_root = Path(__file__).resolve().parents[1] / "resources"
        texture_root = resource_root / "textures"
        sketch_root = resource_root / "sketches_and_strokes"
        self.visual_asset_index = VisualAssetIndex([texture_root, sketch_root])
        self.visual_asset_index.scan()
        self.performance_manager = PerformanceManager()
        self.automation = AutomationDirector()
        self.effects = EffectSettings()
        self.decks: dict[str, VideoDeck] = {
            deck_id: VideoDeck(deck_id) for deck_id in VIDEO_DECK_IDS
        }
        self._frame_snapshots: dict[str, FrameSnapshot] = {}
        self._overlay_frames: dict[str, FrameSnapshot] = {}
        self._overlay_started_at: dict[str, float] = {}
        self._overlay_images: dict[str, ImageOverlayPlayer] = {}
        self._overlay_videos: dict[str, VideoDeck] = {}
        self._automation_collection_id: str | None = None
        self.composition = Composition()
        self.layer_manager = LayerManager(self.composition, self.events)
        self._create_default_layers()
        self.current_project_path: Path | None = None
        self.window: Any | None = None

    def _create_default_layers(self) -> None:
        positions = ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75))
        for index, deck_id in enumerate(VIDEO_DECK_IDS):
            self.composition.add_layer(
                Layer(
                    id=f"layer_{deck_id}",
                    name=f"Video {deck_id[-1].upper()}",
                    source_type="video",
                    source_id=deck_id,
                    visible=True,
                    position=positions[index],
                    scale=(0.5, 0.5),
                    z_index=index,
                )
            )

    def start_osc_receiver(self, bind_address: str = "127.0.0.1", port: int = 57121) -> int:
        """Start the versioned Sonic Pi OSC ingress on a dedicated UDP port."""
        actual_port = self.osc_receiver.start(bind_address, port)
        self.events.publish("performance.osc.started", bind_address=bind_address, port=actual_port)
        return actual_port

    def stop_osc_receiver(self) -> bool:
        """Stop the OSC worker without changing the visual transport state."""
        stopped = self.osc_receiver.stop()
        if stopped:
            self.events.publish("performance.osc.stopped")
        return stopped

    def submit_control_event(self, event: ControlEvent) -> bool:
        """Submit a normalized event from an internal or future external source."""
        return self.control_events.submit(event)

    def process_control_events(self, max_events: int = 128) -> int:
        """Apply a bounded number of queued control events on the UI thread."""
        processed = 0
        for event in self.control_events.drain(max_events):
            try:
                if event.source == "sonic_pi" and event.kind == "transport.start":
                    # Sonic Pi is the clock authority while its session is active.
                    self.transport.stop()
                    self.transport.set_tempo(float(event.payload["bpm"]))
                    self.transport.set_meter(int(event.payload["beats_per_bar"]))
                    self._external_clock_bar_at = None
                elif event.source == "sonic_pi" and event.kind == "transport.tempo":
                    self.transport.set_tempo(float(event.payload["bpm"]))
                elif event.source == "sonic_pi" and event.kind == "clock.bar":
                    # A start datagram can be lost while a later bar still arrives.
                    # Treat the first bar as an authority hand-off too, so the
                    # internal test clock can never run alongside Sonic Pi.
                    self.transport.stop()
                    self.transport.set_tempo(float(event.payload["bpm"]))
                    self.transport.set_meter(int(event.payload["beats_per_bar"]))
                    self._external_clock_bar_at = event.received_at
                elif event.source == "sonic_pi" and event.kind == "transport.stop":
                    self.transport.stop()
                    self._external_clock_bar_at = None
                elif event.source != "sonic_pi" and event.kind == "transport.start":
                    self._external_clock_bar_at = None
                if self.performance_control.apply(event):
                    processed += 1
                    if event.kind == "scene.select":
                        self._activate_scene_profile(str(event.payload["scene_id"]))
            except (TypeError, ValueError, KeyError) as exc:
                _LOG.warning(
                    "Rejected performance control event %s from %s: %s",
                    event.kind,
                    event.source,
                    exc,
                )
        if processed:
            self.events.publish(
                "performance.control.updated",
                state=self.performance_control.snapshot(),
                processed=processed,
            )
        return processed

