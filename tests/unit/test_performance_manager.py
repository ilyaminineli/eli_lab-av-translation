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
