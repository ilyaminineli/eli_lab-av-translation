from __future__ import annotations

import pytest
from PySide6.QtGui import QFont

from generators.catalog import (
    GENERATOR_TYPES,
    animation_code,
    default_generator_settings,
    normalize_settings,
)


@pytest.mark.parametrize("generator_type", GENERATOR_TYPES)
def test_default_generator_settings_are_available(generator_type: str) -> None:
    settings = default_generator_settings(generator_type)

    assert isinstance(settings, dict)
    assert settings["primary_color"].startswith("#")
    assert settings["animation"] in {"none", "pulse", "rotate", "drift", "flicker"}


def test_unknown_generator_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown generator type"):
        default_generator_settings("not-a-generator")


def test_geometry_generator_settings_are_clamped() -> None:
    settings = normalize_settings("geometry", {
        "density": 1000,
        "line_width": -4.0,
        "rotation": 900,
        "animation": "rotate",
        "animation_amount": 900,
    })

    assert settings["density"] == 80
    assert settings["line_width"] == 0.5
    assert settings["rotation"] == 360.0
    assert settings["animation_amount"] == 360.0


def test_text_generator_settings_are_clamped_and_fallback_alignment() -> None:
    settings = normalize_settings("text", {
        "font_size": 1000,
        "font_weight": 1200,
        "letter_spacing": 200,
        "line_spacing": 0.1,
        "alignment": "diagonal",
        "vertical_alignment": "elsewhere",
        "stroke_width": 40,
    })

    assert settings["font_size"] == 420
    assert settings["font_weight"] == 900
    assert settings["letter_spacing"] == 48.0
    assert settings["line_spacing"] == 0.5
    assert settings["alignment"] == "center"
    assert settings["vertical_alignment"] == "middle"
    assert settings["stroke_width"] == 24.0


def test_animation_mapping_is_stable_for_the_gpu_uniform() -> None:
    assert animation_code({"animation": "none"}) == 0
    assert animation_code({"animation": "pulse"}) == 1
    assert animation_code({"animation": "rotate"}) == 2
    assert animation_code({"animation": "drift"}) == 3
    assert animation_code({"animation": "flicker"}) == 4
    assert animation_code({"animation": "unknown"}) == 0


def test_animation_changes_do_not_change_raster_fingerprint(tmp_path) -> None:
    from core.composition import Layer
    from generators.rasterizer import GeneratorRasterizer

    layer = Layer(
        id="text-cache",
        source_type="generator",
        generator_type="text",
        generator_settings=default_generator_settings("text"),
    )
    first = GeneratorRasterizer.fingerprint(layer)
    layer.generator_settings["animation"] = "flicker"
    layer.generator_settings["animation_speed"] = 2.4
    layer.generator_settings["animation_amount"] = 0.2

    assert GeneratorRasterizer.fingerprint(layer) == first


def test_py_side_font_weight_values_convert_to_qt_enum() -> None:
    for weight in (400, 500, 700, 900):
        assert int(QFont.Weight(weight)) == weight


def test_text_weight_normalizes_to_a_supported_qt_weight() -> None:
    settings = normalize_settings("text", {"font_weight": 650})

    assert settings["font_weight"] in (600, 700)


def test_text_generator_has_complete_palette_defaults() -> None:
    settings = default_generator_settings("text")

    assert settings["secondary_color"].startswith("#")
    assert settings["text_color_mode"] == "alternate"


def test_legacy_text_generator_settings_get_accent_colour_fallback() -> None:
    settings = normalize_settings("text", {
        "text": "OLD PROJECT",
        "primary_color": "#FFFFFF",
    })

    assert settings["secondary_color"] == "#C35C75"
    assert settings["text_color_mode"] == "alternate"


def test_invalid_text_colour_mode_falls_back_to_single_colour() -> None:
    settings = normalize_settings("text", {"text_color_mode": "rainbow"})

    assert settings["text_color_mode"] == "single"


@pytest.mark.parametrize(
    ("generator_type", "pattern"),
    [
        ("geometry", "spiral"),
        ("geometry", "moire"),
        ("geometry", "hexgrid"),
        ("waveform", "radial"),
        ("waveform", "rose"),
    ],
)
def test_new_generator_patterns_survive_normalization(
    generator_type: str,
    pattern: str,
) -> None:
    settings = normalize_settings(generator_type, {"pattern": pattern})

    assert settings["pattern"] == pattern


def test_unknown_generator_pattern_returns_to_safe_default() -> None:
    assert normalize_settings("geometry", {"pattern": "invalid"})["pattern"] == "rings"
    assert normalize_settings("waveform", {"pattern": "invalid"})["pattern"] == "sine"
