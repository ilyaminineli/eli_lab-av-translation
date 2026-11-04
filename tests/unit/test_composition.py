from core.composition import Composition, Layer


def test_layer_round_trip_preserves_transform_and_blend() -> None:
    layer = Layer(
        id="layer_1", name="Footage", source_id="deck_a",
        opacity=0.42, blend_mode="screen", position=(0.25, 0.7),
        scale=(0.8, 0.6), rotation=12.5,
    )
    restored = Layer.from_dict(layer.to_dict())
    assert restored.id == layer.id
    assert restored.opacity == 0.42
    assert restored.blend_mode == "screen"
    assert restored.position == (0.25, 0.7)
    assert restored.scale == (0.8, 0.6)
    assert restored.rotation == 12.5


def test_composition_sorts_layers_by_z_index() -> None:
    composition = Composition()
    composition.add_layer(Layer(id="upper", z_index=10))
    composition.add_layer(Layer(id="lower", z_index=0))
    assert [layer.id for layer in composition.layers] == ["lower", "upper"]


def test_duplicate_layer_id_is_rejected() -> None:
    composition = Composition()
    composition.add_layer(Layer(id="same"))
    try:
        composition.add_layer(Layer(id="same"))
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Duplicate layer id should raise ValueError")
