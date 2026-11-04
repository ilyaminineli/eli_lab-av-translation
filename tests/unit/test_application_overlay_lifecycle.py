from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from core.application import Application
from core.composition import Composition
from core.event_bus import EventBus
from core.layer_manager import LayerManager


def make_image(path: Path) -> None:
    image = QImage(8, 4, QImage.Format.Format_RGBA8888)
    image.fill(0)
    image.setPixelColor(2, 1, QColor(255, 255, 255, 255))
    assert image.save(str(path))


def test_application_adds_shared_still_overlay_and_releases_it(tmp_path) -> None:
    path = tmp_path / "texture.png"
    make_image(path)

    application = Application.__new__(Application)
    application.events = EventBus()
    application.composition = Composition()
    application.layer_manager = LayerManager(application.composition, application.events)
    application._overlay_frames = {}
    application._overlay_started_at = {}
    application._overlay_images = {}
    application._overlay_videos = {}
    application._frame_snapshots = {}

    layer = application.add_media_overlay(path)
    frames = application.current_frames()

    assert layer.source_type == "overlay"
    assert layer.overlay_kind == "image"
    assert layer.source_id in frames
    assert layer.id in application._overlay_images

    layer.overlay_in = 60.0
    assert layer.source_id not in application.current_frames()
    layer.overlay_in = 0.0
    layer.overlay_out = 0.01
    application._overlay_started_at[layer.id] -= 1.0
    assert layer.source_id not in application.current_frames()
    layer.overlay_out = None
    assert layer.source_id in application.current_frames()

    removed = application.remove_layer(layer.id)

    assert removed is True
    assert layer.id not in application._overlay_images
    assert layer.id not in application._overlay_frames
    assert layer.source_id not in application.current_frames()



def test_selected_layer_editor_edits_and_removes_overlay(qtbot, tmp_path) -> None:
    from ui.generators_panel import GeneratorsPanel

    path = tmp_path / "editable-overlay.png"
    make_image(path)
    application = Application()
    try:
        layer = application.add_media_overlay(path)
        panel = GeneratorsPanel(application)
        qtbot.addWidget(panel)

        selected_index = panel.layer_combo.findData(layer.id)
        assert selected_index >= 0
        panel.layer_combo.setCurrentIndex(selected_index)
        assert not panel.overlay_group.isHidden()

        panel.opacity_slider.setValue(42)
        panel.blend_mode_combo.setCurrentText("multiply")
        assert layer.opacity == 0.42
        assert layer.blend_mode == "multiply"

        panel.remove_button.click()

        assert application.composition.get_layer(layer.id) is None
        assert layer.id not in application._overlay_images
    finally:
        application.shutdown()
