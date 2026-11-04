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
