from __future__ import annotations

from copy import deepcopy
from typing import Any

GENERATOR_TYPES = ("geometry", "text", "waveform", "particles")

_DEFAULTS: dict[str, dict[str, Any]] = {
    "geometry": {
        "pattern": "rings",
        "primary_color": "#E8E4DA",
        "secondary_color": "#8678A8",
        "background_color": "#00000000",
        "density": 12,
        "line_width": 2.0,
        "rotation": 0.0,
        "animation": "rotate",
        "animation_speed": 0.18,
        "animation_amount": 12.0,
    },
    "text": {
        "text": "THE SHAPE OF\nA VANISHING\nSIGNAL",
        "text_pool_language": "bilingual",
        "text_pool_theme": "random",
        "text_pool_count": 16,
        "text_pool_dictionary": True,
        "text_auto_regenerate": True,
        "font_family": "Arial",
        "font_size": 148,
        "font_weight": 700,
        "letter_spacing": 10.0,
        "line_spacing": 1.0,
        "alignment": "center",
        "vertical_alignment": "middle",
        "primary_color": "#F2EEE6",
        "secondary_color": "#C35C75",
        "text_color_mode": "alternate",
        "text_layout": "single",
        "collage_seed": 211,
        "collage_font_variation": 0.65,
        "text_animation": "none",
        "text_animation_speed": 1.0,
        "text_animation_amount": 0.025,
        "text_animation_columns": 18,
        "stroke_color": "#211B2A",
        "stroke_width": 2.0,
        "shadow": True,
        "animation": "none",
        "animation_speed": 0.2,
        "animation_amount": 0.0,
    },
    "waveform": {
        "pattern": "sine",
        "primary_color": "#E8E4DA",
        "secondary_color": "#C35C75",
        "density": 5,
        "line_width": 3.0,
        "amplitude": 0.22,
        "frequency": 2.5,
        "phase_offset": 0.8,
        "animation": "drift",
        "animation_speed": 0.28,
        "animation_amount": 0.025,
    },
    "particles": {
        "primary_color": "#E8E4DA",
        "secondary_color": "#C35C75",
        "density": 42,
        "speed": 0.22,
        "size": 0.18,
        "spread": 0.42,
        "trail": 0.18,
        "mode": "drift",
        "animation": "none",
        "animation_speed": 0.0,
        "animation_amount": 0.0,
    },
}

_ANIMATIONS = ("none", "pulse", "rotate", "drift", "flicker", "warp")


def default_generator_settings(generator_type: str) -> dict[str, Any]:
    if generator_type not in _DEFAULTS:
        raise ValueError(f"Unknown generator type: {generator_type}")
    return deepcopy(_DEFAULTS[generator_type])


def normalize_settings(generator_type: str, settings: dict[str, Any] | None) -> dict[str, Any]:
    """Merge user settings with safe defaults and clamp resource/visual ranges."""
    result = default_generator_settings(generator_type)
    if settings:
        result.update({
            key: value for key, value in settings.items()
            if key in result
        })

    if generator_type == "geometry":
        if result["pattern"] not in {
            "rings", "grid", "radial", "crosshatch", "polygon",
            "spiral", "moire", "hexgrid",
        }:
            result["pattern"] = "rings"
        result["density"] = max(2, min(80, int(result["density"])))
        result["line_width"] = max(0.5, min(24.0, float(result["line_width"])))
        result["rotation"] = max(-360.0, min(360.0, float(result["rotation"])))
    elif generator_type == "text":
        result["text_pool_language"] = result.get("text_pool_language", "bilingual")
        if result["text_pool_language"] not in {"english", "japanese", "bilingual"}:
            result["text_pool_language"] = "bilingual"
        result["text_pool_theme"] = result.get("text_pool_theme", "random")
        if result["text_pool_theme"] not in {
            "random", "memory", "body", "signal", "ritual", "identity"
        }:
            result["text_pool_theme"] = "random"
        result["text_pool_count"] = max(1, min(60, int(result.get("text_pool_count", 16))))
        result["text_pool_dictionary"] = bool(result.get("text_pool_dictionary", True))
        result["text_auto_regenerate"] = bool(result.get("text_auto_regenerate", True))
        result["font_size"] = max(12, min(420, int(result["font_size"])))
        requested_weight = max(100, min(900, int(result["font_weight"])))
        supported_weights = (100, 200, 300, 400, 500, 600, 700, 800, 900)
        result["font_weight"] = min(
            supported_weights,
            key=lambda weight: abs(weight - requested_weight),
        )
        result["letter_spacing"] = max(-8.0, min(48.0, float(result["letter_spacing"])))
        result["line_spacing"] = max(0.5, min(2.5, float(result["line_spacing"])))
        result["stroke_width"] = max(0.0, min(24.0, float(result["stroke_width"])))
        if result["alignment"] not in {"left", "center", "right"}:
            result["alignment"] = "center"
        if result["vertical_alignment"] not in {"top", "middle", "bottom"}:
            result["vertical_alignment"] = "middle"
        if result.get("text_color_mode") not in {"single", "alternate"}:
            result["text_color_mode"] = "single"
        result["shadow"] = bool(result["shadow"])
        if result.get("text_layout") not in {"single", "collage"}:
            result["text_layout"] = "single"
        result["collage_seed"] = max(0, min(2 ** 31 - 1, int(result["collage_seed"])))
        result["collage_font_variation"] = max(
            0.0, min(1.0, float(result["collage_font_variation"]))
        )
        if result.get("text_animation") not in {
            "none", "type_on", "word_reveal", "line_wave", "jitter", "crawl", "glitch"
        }:
            result["text_animation"] = "none"
        result["text_animation_speed"] = max(
            0.0, min(8.0, float(result["text_animation_speed"]))
        )
        result["text_animation_amount"] = max(
            0.0, min(0.18, float(result["text_animation_amount"]))
        )
        result["text_animation_columns"] = max(
            2, min(80, int(result["text_animation_columns"]))
        )
    elif generator_type == "waveform":
        if result["pattern"] not in {"sine", "lissajous", "orbit", "radial", "rose"}:
            result["pattern"] = "sine"
        result["density"] = max(1, min(12, int(result["density"])))
        result["line_width"] = max(0.5, min(20.0, float(result["line_width"])))
        result["amplitude"] = max(0.01, min(0.48, float(result["amplitude"])))
        result["frequency"] = max(0.1, min(24.0, float(result["frequency"])))
        result["phase_offset"] = max(0.0, min(6.283, float(result["phase_offset"])))
    elif generator_type == "particles":
        result["density"] = max(4, min(120, int(result["density"])))
        result["speed"] = max(0.0, min(2.0, float(result["speed"])))
        result["size"] = max(0.02, min(0.8, float(result["size"])))
        result["spread"] = max(0.0, min(1.0, float(result["spread"])))
        result["trail"] = max(0.0, min(1.0, float(result["trail"])))
        if result.get("mode") not in {"drift", "rise", "fall", "orbit"}:
            result["mode"] = "drift"

    if result.get("animation") not in _ANIMATIONS:
        result["animation"] = "none"
    result["animation_speed"] = max(0.0, min(8.0, float(result["animation_speed"])))
    result["animation_amount"] = max(
        0.0,
        min(360.0 if result["animation"] == "rotate" else 0.45,
            float(result["animation_amount"])),
    )
    return result


def animation_code(settings: dict[str, Any]) -> int:
    """Map animation presets to the compositor's small uniform enum."""
    return {
        "none": 0,
        "pulse": 1,
        "rotate": 2,
        "drift": 3,
        "flicker": 4,
        "warp": 5,
    }.get(str(settings.get("animation", "none")), 0)


def text_animation_code(settings: dict[str, Any]) -> int:
    """Map text-specific motion behaviours to the compositor shader."""
    return {
        "none": 0,
        "type_on": 1,
        "word_reveal": 2,
        "line_wave": 3,
        "jitter": 4,
        "crawl": 5,
        "glitch": 6,
    }.get(str(settings.get("text_animation", "none")), 0)
