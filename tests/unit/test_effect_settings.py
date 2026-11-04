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
