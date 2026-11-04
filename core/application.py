from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import VIDEO_DECK_IDS
from core.automation import AutomationDirector, AutomationSettings
from core.composition import Composition, Layer
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.performance_manager import PerformanceManager
from core.project_manager import ProjectManager
from effects.settings import EffectSettings
from media.frame_queue import FrameSnapshot
from media.library import MediaLibrary
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

    def reset_project(self) -> None:
        self.automation.stop()
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
        return changed

    def current_frames(self) -> dict[str, FrameSnapshot]:
        # Each output has its own GPU context and upload revision.
        return dict(self._frame_snapshots)

    def performance_snapshot(self) -> dict[str, int | float]:
        deck_stats = [deck.performance_stats() for deck in self.decks.values()]
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
        self._frame_snapshots.clear()
        self.events.publish("automation.started", decks=loaded)
        return loaded

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
        for deck in self.decks.values():
            deck.close()
            deck.locked = False

        self._frame_snapshots.clear()
        self.composition = composition
        self.layer_manager = LayerManager(self.composition, self.events)
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
        for deck in self.decks.values():
            deck.close()
        self.events.publish("application.shutdown")
        self.events.clear()
