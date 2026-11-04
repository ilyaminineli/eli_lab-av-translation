from __future__ import annotations

from copy import deepcopy
from typing import Any

LAYER_EFFECT_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "mix": 1.0,
    "monochrome": 0.0,
    "invert": 0.0,
    "threshold": 0.0,
    "posterize": 0.0,
    "hue": 0.0,
    "saturation": 1.0,
    "contrast": 1.0,
    "brightness": 0.0,
    "scanlines": 0.0,
    "chromatic": 0.0,
}

LAYER_EFFECT_PRESETS: dict[str, dict[str, Any]] = {
    "Clean": {},
    "Monochrome": {"monochrome": 1.0, "contrast": 1.12},
    "Xerox": {
        "monochrome": 1.0,
        "contrast": 1.75,
        "threshold": 0.66,
        "posterize": 0.8,
        "scanlines": 0.08,
    },
    "Negative": {"invert": 1.0, "contrast": 1.08},
    "Duotone": {"monochrome": 0.82, "hue": -28.0, "saturation": 1.5},
    "Ghost": {
        "monochrome": 0.35,
        "chromatic": 0.72,
        "saturation": 1.35,
        "contrast": 1.22,
        "brightness": 0.06,
    },
    "Tape": {
        "chromatic": 0.6,
        "scanlines": 0.48,
        "saturation": 1.18,
        "hue": 8.0,
    },
}


def default_layer_effects() -> dict[str, Any]:
    return deepcopy(LAYER_EFFECT_DEFAULTS)


def normalize_layer_effects(settings: dict[str, Any] | None) -> dict[str, Any]:
    result = default_layer_effects()
    if isinstance(settings, dict):
        result.update({
            key: value for key, value in settings.items()
            if key in result
        })
    result["enabled"] = bool(result["enabled"])
    for key in (
            "mix", "monochrome", "invert", "threshold", "posterize",
            "scanlines", "chromatic",
    ):
        result[key] = max(0.0, min(1.0, float(result[key])))
    result["hue"] = max(-180.0, min(180.0, float(result["hue"])))
    result["saturation"] = max(0.0, min(2.5, float(result["saturation"])))
    result["contrast"] = max(0.0, min(2.5, float(result["contrast"])))
    result["brightness"] = max(-0.5, min(0.5, float(result["brightness"])))
    return result


def apply_layer_effect_preset(name: str) -> dict[str, Any]:
    if name not in LAYER_EFFECT_PRESETS:
        raise KeyError(f"Unknown layer effect preset: {name}")
    values = default_layer_effects()
    values["enabled"] = name != "Clean"
    values.update(LAYER_EFFECT_PRESETS[name])
    return normalize_layer_effects(values)
