from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import VIDEO_DECK_IDS
from core.automation import AutomationDirector, AutomationSettings
from core.composition import Composition, Layer
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.performance_manager import PerformanceManager
from core.project_manager import ProjectManager
from effects.settings import EffectSettings
from generators.catalog import GENERATOR_TYPES, default_generator_settings
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
        self.project_manager = ProjectManager()
        self.media_library = MediaLibrary()
        self.performance_manager = PerformanceManager()
        self.automation = AutomationDirector()
        self.effects = EffectSettings()
        self.decks: dict[str, VideoDeck] = {
            deck_id: VideoDeck(deck_id) for deck_id in VIDEO_DECK_IDS
        }
        self._frame_snapshots: dict[str, FrameSnapshot] = {}
        self._overlay_frames: dict[str, FrameSnapshot] = {}
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
        layer.source_id = f"overlay:{layer.id}"
        if kind == "video":
            deck = VideoDeck(f"overlay_{layer.id}")
            deck.load(source, loop=True)
            self._overlay_videos[layer.id] = deck
            self._overlay_frames.pop(layer.id, None)
        else:
            player = ImageOverlayPlayer(source, speed=layer.overlay_speed, frame_hold=layer.overlay_frame_hold)
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
                player.configure_playback(layer.overlay_speed, layer.overlay_frame_hold)
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
        frames.update({
            f"overlay:{layer_id}": snapshot
            for layer_id, snapshot in self._overlay_frames.items()
        })
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
        self.automation.stop()
        self._clear_overlays()
        for deck in self.decks.values():
            deck.close()
        self.events.publish("application.shutdown")
        self.events.clear()
