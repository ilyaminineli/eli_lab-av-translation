from effects.settings import EffectSettings


def test_clean_preset_resets_previous_overlay_values() -> None:
    settings = EffectSettings()
    settings.apply_preset("Digital Damage")

    assert settings.glitch > 0.0
    assert settings.chromatic > 0.0

    settings.apply_preset("Clean")

    assert settings.glitch == 0.0
    assert settings.chromatic == 0.0
    assert settings.grain == 0.0
    assert settings.preset_name == "Clean"


def test_effect_settings_round_trip_and_clamp() -> None:
    settings = EffectSettings.from_dict(
        {"contrast": 9.0, "grain": 1.8, "unknown": 12}
    )

    assert settings.contrast == 2.5
    assert settings.grain == 1.0
    assert "unknown" not in settings.to_dict()



def test_new_effect_controls_are_clamped_and_round_trip() -> None:
    settings = EffectSettings.from_dict({
        "enabled": False,
        "mix": 1.8,
        "exposure": 8.0,
        "temperature": -3.0,
        "tint": 2.0,
        "hue": 300.0,
        "halftone": 1.5,
        "solarize": -0.5,
    })

    assert settings.enabled is False
    assert settings.mix == 1.0
    assert settings.exposure == 2.0
    assert settings.temperature == -1.0
    assert settings.tint == 1.0
    assert settings.hue == 180.0
    assert settings.halftone == 1.0
    assert settings.solarize == 0.0


def test_legacy_effect_project_gets_new_controls_with_safe_defaults() -> None:
    settings = EffectSettings.from_dict({
        "contrast": 1.25,
        "grain": 0.3,
        "preset_name": "Custom",
    })

    assert settings.enabled is True
    assert settings.mix == 1.0
    assert settings.exposure == 0.0
    assert settings.temperature == 0.0
    assert settings.tint == 0.0
    assert settings.hue == 0.0
    assert settings.halftone == 0.0
    assert settings.solarize == 0.0
    assert settings.contrast == 1.25
    assert settings.grain == 0.3


def test_new_effect_looks_reset_all_parameters_between_presets() -> None:
    settings = EffectSettings()
    settings.apply_preset("Infrared")
    assert settings.hue == 128.0
    assert settings.temperature > 0.0

    settings.apply_preset("Clean")
    assert settings.hue == 0.0
    assert settings.temperature == 0.0
    assert settings.halftone == 0.0
    assert settings.enabled is True
    assert settings.mix == 1.0


def test_new_effect_presets_are_available() -> None:
    from effects.settings import PRESETS

    assert {"Halftone Print", "Photocopy", "Infrared", "Cold Steel", "Solarized"} <= set(PRESETS)
