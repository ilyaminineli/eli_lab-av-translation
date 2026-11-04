from effects.layer_settings import (
    LAYER_EFFECT_PRESETS,
    apply_layer_effect_preset,
    normalize_layer_effects,
)


def test_layer_effect_stack_has_neutral_backward_compatible_defaults() -> None:
    values = normalize_layer_effects(None)

    assert values["enabled"] is False
    assert values["mix"] == 1.0
    assert values["monochrome"] == 0.0
    assert values["invert"] == 0.0
    assert values["hue"] == 0.0


def test_layer_effect_stack_clamps_all_user_values() -> None:
    values = normalize_layer_effects({
        "enabled": True,
        "mix": 4.0,
        "monochrome": -1.0,
        "hue": 270,
        "contrast": 9.0,
        "brightness": -2.0,
        "chromatic": 2.0,
    })

    assert values["enabled"] is True
    assert values["mix"] == 1.0
    assert values["monochrome"] == 0.0
    assert values["hue"] == 180.0
    assert values["contrast"] == 2.5
    assert values["brightness"] == -0.5
    assert values["chromatic"] == 1.0


def test_layer_effect_presets_are_complete_and_clean_bypasses() -> None:
    for name in LAYER_EFFECT_PRESETS:
        values = apply_layer_effect_preset(name)
        assert set(values) == set(normalize_layer_effects(None))
        assert values["enabled"] is (name != "Clean")

    xerox = apply_layer_effect_preset("Xerox")
    assert xerox["monochrome"] == 1.0
    assert xerox["threshold"] > 0.0


def test_layer_effect_shader_contains_independent_processing_stages() -> None:
    from rendering.compositor import _COMPOSITE_FRAGMENT

    for symbol in (
        "u_layer_fx_enabled",
        "u_layer_fx_mix",
        "u_layer_fx_monochrome",
        "u_layer_fx_threshold",
        "u_layer_fx_posterize",
        "u_layer_fx_chromatic",
        "layer_color_effects",
    ):
        assert symbol in _COMPOSITE_FRAGMENT


def test_particle_shader_has_gpu_field_and_all_motion_modes() -> None:
    from rendering.compositor import _COMPOSITE_FRAGMENT

    assert "vec4 particle_field(vec2 uv)" in _COMPOSITE_FRAGMENT
    assert "u_particle_density" in _COMPOSITE_FRAGMENT
    assert "u_particle_trail" in _COMPOSITE_FRAGMENT
    assert "u_particle_mode == 3" in _COMPOSITE_FRAGMENT


def test_ordered_effect_chain_preserves_stage_order_and_limits_length() -> None:
    values = normalize_layer_effects({
        "enabled": True,
        "stages": [
            {"type": "invert", "amount": 1.4},
            {"type": "monochrome", "amount": 0.5},
            {"type": "unknown", "amount": 1.0},
        ],
    })
    assert [stage["type"] for stage in values["stages"]] == ["invert", "monochrome"]
    assert values["stages"][0]["amount"] == 1.0
    assert values["stages"][1]["amount"] == 0.5


def test_ordered_fx_stages_and_track_matte_are_in_shared_shader() -> None:
    from rendering.compositor import _COMPOSITE_FRAGMENT
    assert "u_fx_stage_count" in _COMPOSITE_FRAGMENT
    assert "u_fx_stage_type[i]" in _COMPOSITE_FRAGMENT
    assert "u_mask_enabled" in _COMPOSITE_FRAGMENT
    assert "u_mask_mode == 2" in _COMPOSITE_FRAGMENT
