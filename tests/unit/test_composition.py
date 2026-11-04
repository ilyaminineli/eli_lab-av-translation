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


def test_generator_layer_settings_round_trip() -> None:
    layer = Layer(
        id="geometry-1",
        name="Geometry",
        source_type="generator",
        source_id="generator:geometry-1",
        generator_type="geometry",
        generator_settings={
            "pattern": "radial",
            "density": 28,
            "primary_color": "#FF3366",
            "animation": "rotate",
            "animation_amount": 24.0,
        },
    )

    restored = Layer.from_dict(layer.to_dict())

    assert restored.source_type == "generator"
    assert restored.generator_type == "geometry"
    assert restored.generator_settings == layer.generator_settings


def test_legacy_layers_receive_empty_generator_settings() -> None:
    restored = Layer.from_dict({
        "id": "old-layer",
        "name": "Legacy footage",
        "source_type": "video",
        "source_id": "deck_a",
    })

    assert restored.generator_type is None
    assert restored.generator_settings == {}


def test_overlay_timing_playback_and_matte_settings_round_trip() -> None:
    layer = Layer(
        id="overlay-timed",
        source_type="overlay",
        overlay_in=1.25,
        overlay_out=8.5,
        overlay_speed=1.75,
        overlay_frame_hold=3,
        overlay_scene_sync=True,
        overlay_mask_mode="luma",
        overlay_mask_source="overlay:matte",
    )
    restored = Layer.from_dict(layer.to_dict())
    assert restored.overlay_in == 1.25
    assert restored.overlay_out == 8.5
    assert restored.overlay_speed == 1.75
    assert restored.overlay_frame_hold == 3
    assert restored.overlay_scene_sync is True
    assert restored.overlay_mask_mode == "luma"
    assert restored.overlay_mask_source == "overlay:matte"
