from core.composition import Layer
from core.performance_manager import PerformanceManager


def test_random_layout_leaves_locked_layers_unchanged() -> None:
    locked = Layer(id="locked", locked=True, position=(0.5, 0.5), scale=(1.0, 1.0))
    free = Layer(id="free", position=(0.5, 0.5), scale=(1.0, 1.0))
    changed = PerformanceManager(seed=123).randomize_layout([locked, free])
    assert changed == 1
    assert locked.position == (0.5, 0.5)
    assert locked.scale == (1.0, 1.0)
    assert free.position != (0.5, 0.5) or free.scale != (1.0, 1.0)


def test_random_layout_does_not_change_generator_layers() -> None:
    video = Layer(id="video", source_type="video", position=(0.5, 0.5), scale=(1.0, 1.0))
    generator = Layer(
        id="geometry",
        source_type="generator",
        generator_type="geometry",
        position=(0.3, 0.7),
        scale=(0.6, 0.6),
    )

    changed = PerformanceManager(seed=123).randomize_layout([video, generator])

    assert changed == 1
    assert generator.position == (0.3, 0.7)
    assert generator.scale == (0.6, 0.6)
