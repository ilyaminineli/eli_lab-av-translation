from __future__ import annotations

from copy import deepcopy
from typing import Any

GENERATOR_TYPES = ("geometry", "text", "waveform")

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
}

_ANIMATIONS = ("none", "pulse", "rotate", "drift", "flicker")


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
    elif generator_type == "waveform":
        if result["pattern"] not in {"sine", "lissajous", "orbit", "radial", "rose"}:
            result["pattern"] = "sine"
        result["density"] = max(1, min(12, int(result["density"])))
        result["line_width"] = max(0.5, min(20.0, float(result["line_width"])))
        result["amplitude"] = max(0.01, min(0.48, float(result["amplitude"])))
        result["frequency"] = max(0.1, min(24.0, float(result["frequency"])))
        result["phase_offset"] = max(0.0, min(6.283, float(result["phase_offset"])))

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
    }.get(str(settings.get("animation", "none")), 0)
