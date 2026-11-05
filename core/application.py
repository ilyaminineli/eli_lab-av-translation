from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import VIDEO_DECK_IDS
from core.audio_analysis import AudioAnalysisSettings, AudioAnalysisFrame
from core.audio_capture import AudioCaptureService
from core.automation import AutomationDirector, AutomationSettings
from core.composition import Composition, Layer
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.modulation import ModulationMatrix, TARGET_SPECS
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
        self.performance_control = PerformanceControlState()
        self.transport = InternalTransport()
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

    def animation_time(self) -> float:
        return max(0.0, time.perf_counter() - self._animation_started_at)

    def set_window(self, window: Any) -> None:
        self.window = window

    def add_generator_layer(self, generator_type: str) -> Layer:
        if generator_type not in GENERATOR_TYPES:
            raise ValueError(f"Unknown generator type: {generator_type}")
        labels = {
            "geometry": "Geometry Generator",
            "text": "Text Art",
            "waveform": "Waveform Generator",
            "particles": "Particle Field",
        }
        blend_modes = {
            "geometry": "screen",
            "text": "normal",
            "waveform": "screen",
            "particles": "screen",
        }
        layer = self.layer_manager.create_layer(
            name=labels[generator_type],
            source_type="generator",
            generator_type=generator_type,
            generator_settings=default_generator_settings(generator_type),
            blend_mode=blend_modes[generator_type],
            position=(0.5, 0.5),
            scale=(1.0, 1.0),
            z_index=max(
                (item.z_index for item in self.composition.layers),
                default=-1,
            ) + 1,
        )
        layer.source_id = f"generator:{layer.id}"
        self.events.publish("generator.added", layer=layer)
        return layer

    def add_visual_asset_root(self, path: str | Path) -> int:
        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            raise NotADirectoryError(root)
        if root not in self.visual_asset_index.roots:
            self.visual_asset_index.roots.append(root)
        return len(self.visual_asset_index.scan())

    def search_visual_assets(self, query: str = "", purpose: str | None = None,
                             kind: str | None = None, category: str | None = None):
        return self.visual_asset_index.search(query, purpose, kind, category)

    def add_library_asset_overlay(self, asset_id: str) -> Layer:
        asset = next((item for item in self.visual_asset_index.assets if item.id == asset_id), None)
        if asset is None:
            raise KeyError(f"Unknown visual asset: {asset_id}")
        return self.add_media_overlay(asset.path)

    def add_media_overlay(self, path: str | Path) -> Layer:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        layer_id = uuid4().hex
        suffix = source.suffix.lower()
        kind = "video" if suffix in SUPPORTED_VIDEO_EXTENSIONS else "image"
        layer = self.layer_manager.create_layer(
            id=layer_id,
            name=f"Overlay · {source.stem}",
            source_type="overlay",
            source_id=f"overlay:{layer_id}",
            overlay_path=str(source),
            overlay_kind=kind,
            blend_mode="normal",
            position=(0.5, 0.5),
            scale=(1.0, 1.0),
            z_index=max(
                (item.z_index for item in self.composition.layers),
                default=-1,
            ) + 1,
        )
        try:
            self._attach_overlay_layer(layer)
        except Exception:
            self.layer_manager.remove_layer(layer.id)
            raise
        self.events.publish("overlay.added", layer=layer)
        return layer

    def _attach_overlay_layer(self, layer: Layer) -> None:
        if not layer.overlay_path:
            raise ValueError(f"Overlay layer {layer.name} has no media path.")
        source = Path(layer.overlay_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        kind = layer.overlay_kind or (
            "video" if source.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS else "image"
        )
        layer.overlay_kind = kind
        layer.source_type = "overlay"
        import time
        self._overlay_started_at[layer.id] = time.perf_counter()
        layer.source_id = f"overlay:{layer.id}"
        if kind == "video":
            deck = VideoDeck(
                f"overlay_{layer.id}"
            )
            deck.load(source, loop=layer.overlay_loop)
            self._overlay_videos[layer.id] = deck
            self._overlay_frames.pop(layer.id, None)
        else:
            player = ImageOverlayPlayer(
                source,
                speed=layer.overlay_speed,
                frame_hold=layer.overlay_frame_hold,
                loop=layer.overlay_loop,
            )
            self._overlay_images[layer.id] = player
            self._overlay_frames[layer.id] = FrameSnapshot(
                player.revision,
                player.frame,
            )

    def _remove_overlay_runtime(self, layer_id: str) -> None:
        player = self._overlay_images.pop(layer_id, None)
        if player is not None:
            player.close()
        deck = self._overlay_videos.pop(layer_id, None)
        if deck is not None:
            deck.close()
        self._overlay_frames.pop(layer_id, None)
        self._overlay_started_at.pop(layer_id, None)

    def _clear_overlays(self) -> None:
        for layer_id in tuple(self._overlay_images):
            self._remove_overlay_runtime(layer_id)
        for layer_id in tuple(self._overlay_videos):
            self._remove_overlay_runtime(layer_id)
        self._overlay_frames.clear()

    def remove_layer(self, layer_id: str) -> bool:
        layer = self.composition.get_layer(layer_id)
        if layer is not None and layer.source_type == "overlay":
            self._remove_overlay_runtime(layer_id)
        return self.layer_manager.remove_layer(layer_id)

    def reset_project(self) -> None:
        self.automation.stop()
        self._clear_overlays()
        for deck in self.decks.values():
            deck.close()
            deck.locked = False
            deck.set_loop(True)
        self._frame_snapshots.clear()
        self.composition = Composition()
        self.layer_manager = LayerManager(self.composition, self.events)
        self._create_default_layers()
        self.effects.reset()
        self.control_events.clear()
        self.performance_control.reset()
        self.transport.stop()
        self.transport.load_settings({
            "bpm": 120.0,
            "beats_per_bar": 4,
            "phrase_bars": 4,
        })
        self.modulation.load_dict([])
        self.scene_profiles = SceneProfileRegistry()
        self.audio_capture.stop()
        self.audio_capture.update_settings(AudioAnalysisSettings())
        self._audio_sources.clear()
        self._latest_audio_frame = None
        self._modulation_base_values.clear()
        self._selected_layer_id = None
        self.current_project_path = None
        self.events.publish("project.reset")

    def assign_media_to_deck(self, asset: object, deck_id: str) -> None:
        if deck_id not in self.decks:
            raise KeyError(f"Unknown video deck: {deck_id}")
        deck = self.decks[deck_id]
        deck.load(
            str(getattr(asset, "path")),
            asset_id=str(getattr(asset, "id")),
            collection_id=str(getattr(asset, "collection_id")),
        )
        self._frame_snapshots.pop(deck_id, None)
        self.events.publish("deck.loaded", deck_id=deck_id, asset=asset)

    def refresh_frames(self) -> bool:
        changed = False
        for deck_id, deck in self.decks.items():
            if deck.consume_latest_frame() is not None:
                snapshot = deck.snapshot_frame()
                if snapshot is not None:
                    self._frame_snapshots[deck_id] = snapshot
                changed = True
            elif deck.current_frame is None:
                self._frame_snapshots.pop(deck_id, None)

        for layer_id, deck in self._overlay_videos.items():
            if deck.consume_latest_frame() is not None:
                snapshot = deck.snapshot_frame()
                if snapshot is not None:
                    self._overlay_frames[layer_id] = snapshot
                changed = True
            elif deck.current_frame is None:
                self._overlay_frames.pop(layer_id, None)

        for layer_id, player in self._overlay_images.items():
            layer = self.composition.get_layer(layer_id)
            if layer is not None:
                player.configure_playback(
                    layer.overlay_speed,
                    layer.overlay_frame_hold,
                    layer.overlay_loop,
                )
            frame = player.update()
            if frame is not None:
                self._overlay_frames[layer_id] = FrameSnapshot(
                    player.revision,
                    frame,
                )
                changed = True
        return changed

    def current_frames(self) -> dict[str, FrameSnapshot]:
        # Both outputs consume the same CPU snapshots; each owns separate GL textures.
        frames = dict(self._frame_snapshots)
        import time
        now = time.perf_counter()
        for layer_id, snapshot in self._overlay_frames.items():
            layer = self.composition.get_layer(layer_id)
            started = self._overlay_started_at.get(layer_id, now)
            if layer is None:
                continue
            elapsed = now - started
            if elapsed < layer.overlay_in:
                continue
            if layer.overlay_out is not None and elapsed >= layer.overlay_out:
                continue
            frames[f"overlay:{layer_id}"] = snapshot
        return frames

    def performance_snapshot(self) -> dict[str, int | float]:
        deck_stats = [deck.performance_stats() for deck in self.decks.values()]
        deck_stats.extend(
            deck.performance_stats() for deck in self._overlay_videos.values()
        )
        return {
            "playing_decks": sum(bool(item["playing"]) for item in deck_stats),
            "queue_depth": sum(int(item["queue_depth"]) for item in deck_stats),
            "dropped_frames": sum(int(item["dropped_frames"]) for item in deck_stats),
            "retired_workers": sum(int(item["retired_workers"]) for item in deck_stats),
            "published_frames": sum(int(item["published_frames"]) for item in deck_stats),
            "decoded_frames": sum(int(item["decoded_frames"]) for item in deck_stats),
            "decode_time_ms": sum(float(item["decode_time_ms"]) for item in deck_stats),
            "conversion_time_ms": sum(
                float(item["conversion_time_ms"]) for item in deck_stats
            ),
            "skipped_output_frames": sum(
                int(item["skipped_output_frames"]) for item in deck_stats
            ),
        }

    def start_automation(
            self,
            collection_id: str | None = None,
            settings: AutomationSettings | None = None,
            duration_seconds: float | None = 1800.0,
    ) -> int:
        assets = self.media_library.list_assets(collection_id=collection_id)
        loaded = self.automation.start(
            assets,
            self.decks,
            self.composition.layers,
            self.effects,
            settings=settings,
            duration_seconds=duration_seconds,
        )
        self._automation_collection_id = collection_id
        self._frame_snapshots.clear()
        self.events.publish("automation.started", decks=loaded)
        return loaded

    def refresh_automation_media_pool(self) -> bool:
        """Apply media-library changes to Auto Mode without cutting current clips."""
        if not self.automation.running:
            return False
        assets = self.media_library.list_assets(
            collection_id=self._automation_collection_id
        )
        self.automation.replace_assets(assets)
        self.events.publish("automation.media_pool_changed", count=len(assets))
        return True

    def submit_control_event(self, event: ControlEvent) -> bool:
        """Submit a normalized event from an internal or future external source."""
        return self.control_events.submit(event)

    def process_control_events(self, max_events: int = 128) -> int:
        """Apply a bounded number of queued control events on the UI thread."""
        processed = 0
        for event in self.control_events.drain(max_events):
            try:
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

    def start_internal_transport(
            self,
            bpm: float | None = None,
            beats_per_bar: int | None = None,
    ) -> None:
        if bpm is not None:
            self.transport.set_tempo(bpm)
        if beats_per_bar is not None:
            self.transport.set_meter(beats_per_bar)
        for event in self.transport.start():
            self.submit_control_event(event)
        self.process_control_events()

    def pause_internal_transport(self) -> None:
        for event in self.transport.pause():
            self.submit_control_event(event)
        self.process_control_events()

    def resume_internal_transport(self) -> None:
        for event in self.transport.resume():
            self.submit_control_event(event)
        self.process_control_events()

    def stop_internal_transport(self) -> None:
        for event in self.transport.stop():
            self.submit_control_event(event)
        self.process_control_events()

    def set_internal_tempo(self, bpm: float) -> None:
        self.transport.set_tempo(bpm)
        self.submit_control_event(ControlEvent(
            "transport.tempo",
            "internal",
            {"bpm": self.transport.bpm},
        ))
        self.process_control_events()

    def set_transport_meter(self, beats_per_bar: int) -> None:
        self.transport.set_meter(beats_per_bar)
        self.submit_control_event(ControlEvent(
            "transport.meter",
            "internal",
            {"beats_per_bar": self.transport.beats_per_bar},
        ))
        self.process_control_events()

    def request_scene_selection(
            self,
            scene_id: str,
            quantization: Quantization = "bar",
    ) -> None:
        profile = self.scene_profiles.get(scene_id)
        if not self.transport.running or self.transport.paused or quantization == "immediate":
            self.submit_control_event(ControlEvent(
                "scene.select",
                "internal",
                {
                    "scene_id": profile.scene_id,
                    "intensity": profile.intensity,
                    "bar_index": self.performance_control.bar_index,
                },
            ))
            self.process_control_events()
            return
        self.transport.schedule_scene(
            profile.scene_id,
            profile.intensity,
            quantization=quantization,
        )

    def update_scene_profile(self, profile: SceneProfile) -> None:
        self.scene_profiles.update(profile)
        self.events.publish("performance.scene_profiles.updated")

    def _activate_scene_profile(self, scene_id: str) -> None:
        profile = self.scene_profiles.get(scene_id)
        if profile.master_look:
            self.effects.apply_preset(profile.master_look)
        try:
            palette = palette_look(profile.palette)
        except KeyError:
            palette = None
        if palette:
            for layer in self.composition.layers:
                if layer.source_type != "generator" or not layer.generator_type:
                    continue
                values = dict(layer.generator_settings)
                for key in ("primary_color", "secondary_color", "background_color"):
                    if key in values and key in palette:
                        values[key] = palette[key]
                layer.generator_settings = normalize_settings(layer.generator_type, values)
        self.events.publish(
            "performance.scene.activated",
            profile=profile.to_dict(),
            state=self.performance_control.snapshot(),
        )

    def set_layer_locked(self, layer_id: str, locked: bool) -> None:
        layer = self.composition.get_layer(layer_id)
        if layer is None or layer.locked == bool(locked):
            return
        target_ids = (
            "selected_layer.opacity",
            "selected_layer.rotation",
            "generator.animation_amount",
            "generator.density",
        )
        if locked and layer_id == self._selected_layer_id:
            for target_id in target_ids:
                base = self._modulation_base_values.pop(target_id, None)
                if base is not None:
                    self._set_modulation_target(target_id, base)
                self.modulation.manual_override(target_id, 0.25)
        layer.locked = bool(locked)
        self.events.publish("layer.locked", layer_id=layer_id, locked=layer.locked)

    def set_selected_layer_id(self, layer_id: str | None) -> None:
        next_id = layer_id or None
        previous_id = self._selected_layer_id
        if next_id == previous_id:
            return
        target_ids = (
            "selected_layer.opacity",
            "selected_layer.rotation",
            "generator.animation_amount",
            "generator.density",
        )
        if previous_id is not None:
            for target_id in target_ids:
                base = self._modulation_base_values.pop(target_id, None)
                if base is not None:
                    self._set_modulation_target(target_id, base)
                self.modulation.manual_override(target_id, 0.25)
        self._selected_layer_id = next_id

    def start_audio_capture(self, device_id: str | None = None, test_signal: bool = False) -> None:
        if test_signal:
            self.audio_capture.start_test_signal(self.transport.bpm)
        elif device_id:
            self.audio_capture.start(device_id)
        else:
            raise ValueError("Select an audio input or system-loopback device first.")
        self._audio_sources.clear()
        self._latest_audio_frame = None
        self.events.publish(
            "audio.capture.started",
            source=self.audio_capture.source_kind,
            device=self.audio_capture.selected_device_name,
        )

    def start_audio_replay(
            self,
            samples,
            sample_rate: int,
            repeat: bool = False,
    ) -> None:
        self.audio_capture.start_replay(samples, sample_rate, repeat=repeat)
        self._audio_sources.clear()
        self._latest_audio_frame = None

    def stop_audio_capture(self) -> bool:
        stopped = self.audio_capture.stop()
        self._audio_sources.clear()
        self.events.publish("audio.capture.stopped", stopped=stopped)
        return stopped

    def update_audio_analysis_settings(self, settings: AudioAnalysisSettings) -> None:
        settings.normalize()
        self.audio_capture.update_settings(settings)

    def process_audio_frames(self, max_frames: int = 4) -> int:
        frames = self.audio_capture.drain_frames(max_frames)
        if not frames:
            return 0
        self._latest_audio_frame = frames[-1]
        self._audio_sources = self._latest_audio_frame.sources()
        self.events.publish(
            "audio.analysis.updated",
            features=self._audio_sources.copy(),
            source=self.audio_capture.source_kind,
        )
        return len(frames)

    def audio_analysis_snapshot(self) -> dict[str, float | str | None]:
        frame = self._latest_audio_frame
        if frame is None:
            return {
                "rms": 0.0,
                "low": 0.0,
                "mid": 0.0,
                "high": 0.0,
                "onset": 0.0,
                "bpm": None,
                "beat_confidence": 0.0,
            }
        return {
            "rms": frame.rms,
            "low": frame.low,
            "mid": frame.mid,
            "high": frame.high,
            "onset": frame.onset,
            "bpm": frame.bpm,
            "beat_confidence": frame.beat_confidence,
        }

    def _modulation_sources(self) -> dict[str, float]:
        values = dict(self._audio_sources)
        values["transport.intensity"] = self.performance_control.intensity
        values["transport.phase"] = self.transport.phase
        for name, value in self.performance_control.macros.items():
            values[f"macro.{name}"] = value
        return values

    def _get_modulation_target(self, target_id: str) -> float | None:
        if target_id.startswith("master."):
            field = target_id.split(".", 1)[1]
            if field in {
                "brightness", "exposure", "contrast", "saturation",
                "grain", "glitch", "vignette",
            }:
                return float(getattr(self.effects, field))
            return None
        if target_id.startswith("selected_layer."):
            layer = self.composition.get_layer(self._selected_layer_id or "")
            if layer is None or layer.locked:
                return None
            field = target_id.split(".", 1)[1]
            if field in {"opacity", "rotation"}:
                return float(getattr(layer, field))
            return None
        if target_id.startswith("generator."):
            layer = self.composition.get_layer(self._selected_layer_id or "")
            if layer is None or layer.locked or layer.source_type != "generator":
                return None
            field = target_id.split(".", 1)[1]
            if field in {"animation_amount", "density"}:
                value = layer.generator_settings.get(field)
                return float(value) if isinstance(value, (int, float)) else None
            return None
        if target_id == "automation.loop_probability":
            return float(self.automation.settings.loop_probability)
        if target_id == "automation.cut_interval":
            return float(self.automation.settings.min_cut_interval)
        return None

    def _set_modulation_target(self, target_id: str, value: float) -> bool:
        if target_id.startswith("master."):
            field = target_id.split(".", 1)[1]
            if field in {
                "brightness", "exposure", "contrast", "saturation",
                "grain", "glitch", "vignette",
            }:
                setattr(self.effects, field, float(value))
                self.effects.preset_name = "Custom"
                return True
            return False
        if target_id.startswith("selected_layer."):
            layer = self.composition.get_layer(self._selected_layer_id or "")
            if layer is None or layer.locked:
                return False
            field = target_id.split(".", 1)[1]
            if field in {"opacity", "rotation"}:
                setattr(layer, field, float(value))
                self.events.publish("layer.modulated", layer_id=layer.id, target=target_id)
                return True
            return False
        if target_id.startswith("generator."):
            layer = self.composition.get_layer(self._selected_layer_id or "")
            if layer is None or layer.locked or layer.source_type != "generator":
                return False
            field = target_id.split(".", 1)[1]
            if field not in {"animation_amount", "density"} or not layer.generator_type:
                return False
            settings = dict(layer.generator_settings)
            settings[field] = value
            layer.generator_settings = normalize_settings(layer.generator_type, settings)
            self.events.publish("layer.modulated", layer_id=layer.id, target=target_id)
            return True
        if target_id == "automation.loop_probability":
            self.automation.settings.loop_probability = max(0.0, min(1.0, float(value)))
            return True
        if target_id == "automation.cut_interval":
            minimum = max(1.0, min(60.0, float(value)))
            self.automation.settings.min_cut_interval = minimum
            self.automation.settings.max_cut_interval = max(
                minimum,
                self.automation.settings.max_cut_interval,
            )
            return True
        return False

    def notify_layer_manual_override(
            self,
            layer_id: str,
            duration_seconds: float = 3.0,
    ) -> None:
        if layer_id == self._selected_layer_id:
            self.notify_manual_override("selected_layer.*", duration_seconds)

    def notify_manual_override(
            self,
            target_id: str,
            duration_seconds: float = 3.0,
    ) -> None:
        targets = (
            [key for key, spec in TARGET_SPECS.items() if spec.category == "master"]
            if target_id == "master.*"
            else [key for key in TARGET_SPECS if key.startswith(target_id)]
            if target_id.endswith(".*")
            else [target_id]
        )
        for key in targets:
            current = self._get_modulation_target(key)
            if current is not None:
                self._modulation_base_values[key] = current
            self.modulation.manual_override(key, duration_seconds)

    def apply_modulation(self) -> dict[str, float]:
        outputs, released = self.modulation.evaluate(self._modulation_sources())
        for target_id in released:
            base = self._modulation_base_values.pop(target_id, None)
            if base is not None:
                self._set_modulation_target(target_id, base)
        for target_id, value in outputs.items():
            if target_id not in self._modulation_base_values:
                base = self._get_modulation_target(target_id)
                if base is None:
                    continue
                self._modulation_base_values[target_id] = base
            self._set_modulation_target(target_id, value)
        return outputs

    def add_modulation_route(self, route) -> None:
        self.modulation.add_route(route)
        self.events.publish("performance.modulation.updated")

    def update_modulation_route(
            self,
            route_id: str,
            changes: dict[str, object],
    ) -> None:
        existing = next(
            (route for route in self.modulation.routes if route.route_id == route_id),
            None,
        )
        if existing is None:
            raise KeyError(f"Unknown modulation route: {route_id}")
        previous_target = existing.target_id
        self.modulation.update_route(route_id, changes)
        updated = next(
            route for route in self.modulation.routes if route.route_id == route_id
        )
        if previous_target != updated.target_id:
            base = self._modulation_base_values.pop(previous_target, None)
            if base is not None:
                self._set_modulation_target(previous_target, base)
        self.events.publish("performance.modulation.updated")

    def remove_modulation_route(self, route_id: str) -> None:
        self.modulation.remove_route(route_id)
        outputs, released = self.modulation.evaluate(self._modulation_sources())
        for target_id in released:
            base = self._modulation_base_values.pop(target_id, None)
            if base is not None:
                self._set_modulation_target(target_id, base)
        self.events.publish("performance.modulation.updated")

    def tick_performance_control(self) -> int:
        clock_events = self.transport.tick()
        for event in clock_events:
            self.submit_control_event(event)
        processed_events = self.process_control_events()
        processed_audio = self.process_audio_frames()
        self.apply_modulation()
        return processed_events + processed_audio + len(clock_events)

    def tick_automation(self) -> bool:
        changed = self.automation.tick()
        if changed:
            for deck_id, deck in self.decks.items():
                if deck.current_frame is None:
                    self._frame_snapshots.pop(deck_id, None)
            self.events.publish("automation.changed", action=self.automation.last_action)
        return changed

    def stop_automation(self) -> None:
        self.automation.stop()
        self._automation_collection_id = None
        self.events.publish("automation.stopped")

    def save_project(self, path: str | Path) -> Path:
        deck_states = [deck.to_dict() for deck in self.decks.values()]
        app_state = {
            "effects": self.effects.to_dict(),
            "automation_settings": self.automation.settings.to_dict(),
            "performance_settings": {
                "transport": self.transport.to_dict(),
                "audio_analysis": self.audio_capture.settings.to_dict(),
                "modulation_routes": self.modulation.to_dict(),
                "scene_profiles": self.scene_profiles.to_dict(),
            },
        }
        saved_path = self.project_manager.save(
            path,
            self.composition,
            deck_states,
            app_state=app_state,
        )
        self.current_project_path = saved_path
        self.events.publish("project.saved", path=saved_path)
        return saved_path

    def load_project(self, path: str | Path) -> None:
        composition, deck_states = self.project_manager.load(path)
        self.control_events.clear()
        self.performance_control.reset()
        self.transport.stop()
        self.transport.load_settings({
            "bpm": 120.0,
            "beats_per_bar": 4,
            "phrase_bars": 4,
        })
        self.audio_capture.update_settings(AudioAnalysisSettings())
        self.scene_profiles = SceneProfileRegistry()
        self.modulation.reset_runtime()
        self._modulation_base_values.clear()
        self.automation.stop()
        self._clear_overlays()
        for deck in self.decks.values():
            deck.close()
            deck.locked = False

        self._frame_snapshots.clear()
        self.composition = composition
        self.layer_manager = LayerManager(self.composition, self.events)
        for layer in self.composition.layers:
            if layer.source_type == "overlay":
                try:
                    self._attach_overlay_layer(layer)
                except Exception as exc:
                    _LOG.warning("Could not restore overlay %s: %s", layer.name, exc)

        for state in deck_states:
            deck_id = str(state.get("id", ""))
            if deck_id not in self.decks:
                continue
            deck = self.decks[deck_id]
            deck.set_loop(bool(state.get("loop", True)))
            deck.locked = bool(state.get("locked", False))
            media_path = state.get("path")
            if media_path and Path(media_path).exists():
                deck.load(
                    str(media_path),
                    asset_id=state.get("asset_id"),
                    collection_id=state.get("collection_id"),
                    segment_start=float(state.get("segment_start", 0.0)),
                    segment_end=state.get("segment_end"),
                    loop=bool(state.get("loop", True)),
                )
            elif media_path:
                _LOG.warning("Project media is missing: %s", media_path)

        app_state = self.project_manager.last_app_state
        self.audio_capture.stop()
        self._audio_sources.clear()
        self._latest_audio_frame = None
        self.modulation.reset_runtime()
        self._modulation_base_values.clear()
        performance_settings = app_state.get("performance_settings", {})
        if isinstance(performance_settings, dict):
            if isinstance(performance_settings.get("transport"), dict):
                self.transport.load_settings(performance_settings["transport"])
            if isinstance(performance_settings.get("audio_analysis"), dict):
                allowed_audio = AudioAnalysisSettings.__dataclass_fields__
                audio_values = {
                    key: value for key, value in performance_settings["audio_analysis"].items()
                    if key in allowed_audio
                }
                self.update_audio_analysis_settings(AudioAnalysisSettings(**audio_values))
            self.modulation.load_dict(performance_settings.get("modulation_routes", []))
            self.scene_profiles.load_dict(performance_settings.get("scene_profiles", []))
        self.performance_control.bpm = self.transport.bpm
        self.performance_control.beats_per_bar = self.transport.beats_per_bar
        if isinstance(app_state.get("effects"), dict):
            loaded_effects = EffectSettings.from_dict(app_state["effects"])
            for key, value in loaded_effects.to_dict().items():
                setattr(self.effects, key, value)
        if isinstance(app_state.get("automation_settings"), dict):
            allowed = AutomationSettings.__dataclass_fields__
            values = {
                key: value for key, value in app_state["automation_settings"].items()
                if key in allowed
            }
            self.automation.settings = AutomationSettings(**values)
            self.automation.settings.normalize()

        self.current_project_path = Path(path).resolve()
        self.events.publish("project.loaded", path=self.current_project_path)

    def shutdown(self) -> None:
        self.control_events.clear()
        self.audio_capture.shutdown()
        self.transport.stop()
        self.modulation.reset_runtime()
        self.automation.stop()
        self._clear_overlays()
        for deck in self.decks.values():
            deck.close()
        self.events.publish("application.shutdown")
        self.events.clear()
