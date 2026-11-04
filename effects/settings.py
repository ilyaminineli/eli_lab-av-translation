from __future__ import annotations

from dataclasses import asdict, dataclass, fields

PRESETS: dict[str, dict[str, float]] = {
    "Clean": {},
    "16mm Film": {
        "contrast": 1.12, "saturation": 0.82, "vignette": 0.38,
        "grain": 0.42, "scanlines": 0.05, "chromatic": 0.06,
    },
    "VHS / Tape": {
        "contrast": 1.08, "saturation": 1.12, "vignette": 0.25,
        "grain": 0.34, "scanlines": 0.36, "chromatic": 0.52, "glitch": 0.28,
    },
    "CRT": {
        "contrast": 1.18, "saturation": 0.92, "vignette": 0.58,
        "scanlines": 0.62, "pixelate": 0.16, "chromatic": 0.12,
    },
    "Bleach Bypass": {
        "contrast": 1.42, "saturation": 0.24, "gamma": 0.92, "vignette": 0.2,
    },
    "Dream Haze": {
        "brightness": 0.07, "contrast": 0.86, "saturation": 1.28,
        "gamma": 1.12, "chromatic": 0.18, "grain": 0.08,
    },
    "Digital Damage": {
        "contrast": 1.22, "saturation": 1.18, "grain": 0.18,
        "scanlines": 0.12, "chromatic": 0.62, "glitch": 0.74, "pixelate": 0.08,
    },
}


@dataclass
class EffectSettings:
    """Master post-processing controls shared by preview and projector output."""

    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0
    vignette: float = 0.0
    grain: float = 0.0
    scanlines: float = 0.0
    chromatic: float = 0.0
    glitch: float = 0.0
    pixelate: float = 0.0
    posterize: float = 0.0
    invert: float = 0.0
    preset_name: str = "Clean"

    def apply_preset(self, name: str) -> None:
        if name not in PRESETS:
            raise KeyError(f"Unknown effect preset: {name}")
        self.reset()
        for field_name, value in PRESETS[name].items():
            setattr(self, field_name, value)
        self.preset_name = name

    def reset(self) -> None:
        defaults = type(self)()
        for item in fields(self):
            setattr(self, item.name, getattr(defaults, item.name))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> EffectSettings:
        allowed = {item.name for item in fields(cls)}
        values = {key: value for key, value in data.items() if key in allowed}
        settings = cls(**values)
        settings.clamp()
        return settings

    def clamp(self) -> None:
        self.brightness = max(-0.5, min(0.5, float(self.brightness)))
        self.contrast = max(0.0, min(2.5, float(self.contrast)))
        self.saturation = max(0.0, min(2.5, float(self.saturation)))
        self.gamma = max(0.2, min(2.5, float(self.gamma)))
        for name in (
            "vignette", "grain", "scanlines", "chromatic",
            "glitch", "pixelate", "posterize", "invert",
        ):
            setattr(self, name, max(0.0, min(1.0, float(getattr(self, name)))))
