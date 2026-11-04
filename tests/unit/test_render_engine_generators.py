from __future__ import annotations

import numpy as np

from core.composition import Composition, Layer
from core.render_engine import RenderEngine


class FakeCompositor:
    def __init__(self) -> None:
        self.uploaded: dict[str, np.ndarray] = {}
        self.removed: list[str] = []
        self.rendered_layers: list[Layer] = []

    def update_texture(self, source_id: str, pixels: np.ndarray) -> None:
        self.uploaded[source_id] = pixels

    def remove_texture(self, source_id: str) -> None:
        self.removed.append(source_id)
        self.uploaded.pop(source_id, None)

    def render(
            self,
            layers,
            target_fbo,
            width,
            height,
            effects=None,
            time_seconds=0.0,
            canvas_width=1920,
            canvas_height=1080,
    ) -> None:
        self.rendered_layers = list(layers)


class FakeRasterizer:
    def __init__(self) -> None:
        self.missing_ids: set[str] = set()

    def render(self, layer: Layer) -> tuple[str, np.ndarray]:
        if layer.id == "broken":
            raise ValueError("bad text settings")
        return "stable-fingerprint", np.zeros((2, 2, 4), dtype=np.uint8)

    def remove_missing(self, layer_ids: set[str]) -> None:
        self.missing_ids = set(layer_ids)

    def clear(self) -> None:
        self.missing_ids.clear()


def test_broken_generator_is_skipped_without_aborting_composition() -> None:
    engine = RenderEngine()
    engine.initialized = True
    engine.compositor = FakeCompositor()
    engine.generator_rasterizer = FakeRasterizer()
    composition = Composition(layers=[
        Layer(
            id="broken",
            name="Bad text",
            source_type="generator",
            source_id="generator:broken",
            generator_type="text",
        ),
        Layer(
            id="good",
            name="Good geometry",
            source_type="generator",
            source_id="generator:good",
            generator_type="geometry",
        ),
    ])

    engine.render(composition, {}, 1, 640, 360)

    assert "generator:broken" in engine.compositor.removed
    assert "generator:good" in engine.compositor.uploaded
    assert engine._generator_errors["broken"] == "bad text settings"
    assert "good" not in engine._generator_errors
    assert engine.compositor.rendered_layers == composition.layers
