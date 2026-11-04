from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from core.composition import Layer
from media.image_overlay import ImageOverlayPlayer


def test_still_image_overlay_loads_transparent_rgba_frame(tmp_path) -> None:
    path = Path(tmp_path) / "overlay.png"
    image = QImage(4, 3, QImage.Format.Format_RGBA8888)
    image.fill(0)
    image.setPixelColor(1, 1, 0x80FFFFFF)
    assert image.save(str(path))

    player = ImageOverlayPlayer(path)
    frame = player.frame

    assert frame.pixels.shape == (3, 4, 4)
    assert frame.pixels.dtype == np.uint8
    assert frame.pixels[0, 0, 3] == 0
    assert frame.pixels[1, 1, 3] > 0
    assert player.update(now=10**9) is None
    player.close()


def test_overlay_layer_media_and_layer_effects_survive_serialization() -> None:
    layer = Layer(
        id="overlay-a",
        name="Paper overlay",
        source_type="overlay",
        source_id="overlay:overlay-a",
        overlay_path="C:/Assets/paper.png",
        overlay_kind="image",
        layer_effects={"enabled": True, "monochrome": 1.0},
    )

    restored = Layer.from_dict(layer.to_dict())

    assert restored.overlay_path == layer.overlay_path
    assert restored.overlay_kind == "image"
    assert restored.layer_effects == layer.layer_effects
