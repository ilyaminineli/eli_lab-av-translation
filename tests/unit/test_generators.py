from __future__ import annotations

import pytest
from PySide6.QtGui import QFont

from generators.catalog import (
    GENERATOR_TYPES,
    animation_code,
    default_generator_settings,
    normalize_settings,
    text_animation_code,
)


@pytest.mark.parametrize("generator_type", GENERATOR_TYPES)
def test_default_generator_settings_are_available(generator_type: str) -> None:
    settings = default_generator_settings(generator_type)

    assert isinstance(settings, dict)
    assert settings["primary_color"].startswith("#")
    assert settings["animation"] in {"none", "pulse", "rotate", "drift", "flicker", "warp"}


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
    assert animation_code({"animation": "warp"}) == 5
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


def test_particle_generator_settings_are_bounded() -> None:
    settings = normalize_settings("particles", {
        "density": 500,
        "speed": 9.0,
        "size": -1.0,
        "spread": 2.0,
        "trail": -0.5,
        "mode": "unknown",
    })

    assert settings["density"] == 120
    assert settings["speed"] == 2.0
    assert settings["size"] == 0.02
    assert settings["spread"] == 1.0
    assert settings["trail"] == 0.0
    assert settings["mode"] == "drift"


def test_text_animation_modes_map_to_gpu_codes() -> None:
    expected = {
        "none": 0,
        "type_on": 1,
        "word_reveal": 2,
        "line_wave": 3,
        "jitter": 4,
        "crawl": 5,
        "glitch": 6,
    }
    for mode, code in expected.items():
        assert text_animation_code({"text_animation": mode}) == code


def test_text_animation_changes_do_not_invalidate_static_raster() -> None:
    from core.composition import Layer
    from generators.rasterizer import GeneratorRasterizer

    settings = default_generator_settings("text")
    layer = Layer(
        id="animated-text",
        source_type="generator",
        generator_type="text",
        generator_settings=settings,
    )
    original = GeneratorRasterizer.fingerprint(layer)
    layer.generator_settings["text_animation"] = "line_wave"
    layer.generator_settings["text_animation_speed"] = 4.0
    layer.generator_settings["text_animation_amount"] = 0.1

    assert GeneratorRasterizer.fingerprint(layer) == original


def test_text_layout_changes_invalidate_static_raster() -> None:
    from core.composition import Layer
    from generators.rasterizer import GeneratorRasterizer

    layer = Layer(
        id="collage-text",
        source_type="generator",
        generator_type="text",
        generator_settings=default_generator_settings("text"),
    )
    first = GeneratorRasterizer.fingerprint(layer)
    layer.generator_settings["text_layout"] = "collage"

    assert GeneratorRasterizer.fingerprint(layer) != first


def test_japanese_palette_looks_are_complete_and_use_valid_hex_values() -> None:
    from generators.palettes import JP_PALETTE_LOOKS, palette_look

    assert len(JP_PALETTE_LOOKS) >= 8
    for name, colours in JP_PALETTE_LOOKS.items():
        assert len(colours) == 4
        assert all(len(value) == 7 and value.startswith("#") for value in colours)
        assert palette_look(name)["primary_color"] == colours[0]


def test_aco_import_reads_named_rgb_swatches_and_builds_four_colour_looks(tmp_path) -> None:
    import struct

    from generators.palettes import import_aco_palette, palette_look

    names = ("Sakura", "Beni", "Ai", "Sumi")
    colours = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (32, 32, 32))
    payload = bytearray(struct.pack(">HH", 2, len(names)))
    for name, rgb in zip(names, colours):
        payload.extend(struct.pack(">5H", 0, *(value * 257 for value in rgb), 0))
        encoded = name.encode("utf-16-be") + bytes(2)
        payload.extend(struct.pack(">I", len(name) + 1))
        payload.extend(encoded)
    aco_path = tmp_path / "jp_palette.aco"
    aco_path.write_bytes(payload)

    imported = import_aco_palette(aco_path)
    look = palette_look(imported[0])
    assert len(imported) == 1
    assert look["primary_color"] == "#FF0000"
    assert look["secondary_color"] == "#00FF00"
    assert look["background_color"] == "#202020"
