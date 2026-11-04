from core.composition import Composition, Layer
from core.layer_manager import LayerManager


def test_layer_manager_updates_layer_and_clamps_opacity() -> None:
    composition = Composition()
    composition.add_layer(Layer(id="layer-a"))
    updated = LayerManager(composition).update_layer(
        "layer-a", opacity=1.8, visible=False
    )
    assert updated.opacity == 1.0
    assert updated.visible is False


def test_layer_manager_removes_layer() -> None:
    composition = Composition()
    composition.add_layer(Layer(id="layer-a"))
    assert LayerManager(composition).remove_layer("layer-a") is True
    assert composition.layers == []
