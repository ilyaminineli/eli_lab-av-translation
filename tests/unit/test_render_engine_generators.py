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


def test_gpu_particle_layer_is_not_sent_through_cpu_rasterizer() -> None:
    class ParticleRejectingRasterizer(FakeRasterizer):
        def render(self, layer: Layer) -> tuple[str, np.ndarray]:
            if layer.generator_type == "particles":
                raise AssertionError("GPU particles must not be CPU-rasterized")
            return super().render(layer)

    engine = RenderEngine()
    engine.initialized = True
    engine.compositor = FakeCompositor()
    engine.generator_rasterizer = ParticleRejectingRasterizer()
    particle = Layer(
        id="particles",
        name="Particles",
        source_type="generator",
        source_id="generator:particles",
        generator_type="particles",
        generator_settings={
            "density": 42,
            "speed": 0.22,
            "size": 0.18,
            "spread": 0.42,
            "trail": 0.18,
            "mode": "drift",
            "primary_color": "#E8E4DA",
            "secondary_color": "#C35C75",
        },
    )
    composition = Composition(layers=[particle])

    engine.render(composition, {}, 1, 640, 360)

    assert "generator:particles" not in engine.compositor.uploaded
    assert engine.compositor.rendered_layers == [particle]
