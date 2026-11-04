from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import VIDEO_DECK_IDS
from core.composition import Composition, Layer
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.performance_manager import PerformanceManager
from core.project_manager import ProjectManager
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
        self.decks: dict[str, VideoDeck] = {
            deck_id: VideoDeck(deck_id) for deck_id in VIDEO_DECK_IDS
        }
        self.composition = Composition()
        self.layer_manager = LayerManager(self.composition, self.events)
        self._create_default_layers()
        self.current_project_path: Path | None = None
        self.window: Any | None = None

    def _create_default_layers(self) -> None:
        # A 2x2 layout makes four loaded decks visible without requiring randomization.
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
        for deck in self.decks.values():
            deck.close()
            deck.locked = False
            deck.set_loop(True)
        self.composition = Composition()
        self.layer_manager = LayerManager(self.composition, self.events)
        self._create_default_layers()
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
        self.events.publish("deck.loaded", deck_id=deck_id, asset=asset)

    def current_frames(self) -> dict[str, object]:
        # Only pass newly decoded frames. The GPU texture retains the last uploaded frame.
        frames: dict[str, object] = {}
        for deck_id, deck in self.decks.items():
            frame = deck.consume_latest_frame()
            if frame is not None:
                frames[deck_id] = frame
        return frames

    def save_project(self, path: str | Path) -> Path:
        deck_states = [deck.to_dict() for deck in self.decks.values()]
        saved_path = self.project_manager.save(path, self.composition, deck_states)
        self.current_project_path = saved_path
        self.events.publish("project.saved", path=saved_path)
        return saved_path

    def load_project(self, path: str | Path) -> None:
        composition, deck_states = self.project_manager.load(path)
        for deck in self.decks.values():
            deck.close()
            deck.locked = False

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
                )
            elif media_path:
                _LOG.warning("Project media is missing: %s", media_path)

        self.current_project_path = Path(path).resolve()
        self.events.publish("project.loaded", path=self.current_project_path)

    def shutdown(self) -> None:
        for deck in self.decks.values():
            deck.close()
        self.events.publish("application.shutdown")
        self.events.clear()
