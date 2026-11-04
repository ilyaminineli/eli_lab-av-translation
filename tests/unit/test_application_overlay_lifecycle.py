from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage

from core.application import Application
from core.composition import Composition
from core.event_bus import EventBus
from core.layer_manager import LayerManager


def make_image(path: Path) -> None:
    image = QImage(8, 4, QImage.Format.Format_RGBA8888)
    image.fill(0)
    image.setPixelColor(2, 1, __import__("PySide6").QtGui.QColor(255, 255, 255, 255))
    assert image.save(str(path))


def test_application_adds_shared_still_overlay_and_releases_it(tmp_path) -> None:
    path = tmp_path / "texture.png"
    make_image(path)

    application = Application.__new__(Application)
    application.events = EventBus()
    application.composition = Composition()
    application.layer_manager = LayerManager(application.composition, application.events)
    application._overlay_frames = {}
    application._overlay_images = {}
    application._overlay_videos = {}
    application._frame_snapshots = {}

    layer = application.add_media_overlay(path)
    frames = application.current_frames()

    assert layer.source_type == "overlay"
    assert layer.overlay_kind == "image"
    assert layer.source_id in frames
    assert layer.id in application._overlay_images

    removed = application.remove_layer(layer.id)

    assert removed is True
    assert layer.id not in application._overlay_images
    assert layer.id not in application._overlay_frames
    assert layer.source_id not in application.current_frames()
