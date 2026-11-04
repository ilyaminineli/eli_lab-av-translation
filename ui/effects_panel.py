from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from effects.settings import PRESETS, EffectSettings

_SLIDERS = (
    ("mix", "Effect mix", 0, 100, 100.0),
    ("brightness", "Brightness", -50, 50, 100.0),
    ("exposure", "Exposure", -200, 200, 100.0),
    ("contrast", "Contrast", 25, 225, 100.0),
    ("saturation", "Saturation", 0, 225, 100.0),
    ("gamma", "Gamma", 25, 225, 100.0),
    ("temperature", "Temperature", -100, 100, 100.0),
    ("tint", "Tint", -100, 100, 100.0),
    ("hue", "Hue shift", -180, 180, 1.0),
    ("vignette", "Vignette", 0, 100, 100.0),
    ("grain", "Film grain", 0, 100, 100.0),
    ("scanlines", "Scanlines", 0, 100, 100.0),
    ("chromatic", "RGB split", 0, 100, 100.0),
    ("glitch", "Signal glitch", 0, 100, 100.0),
    ("pixelate", "Pixelation", 0, 100, 100.0),
    ("posterize", "Posterize", 0, 100, 100.0),
    ("invert", "Invert", 0, 100, 100.0),
    ("halftone", "Halftone print", 0, 100, 100.0),
    ("solarize", "Solarization", 0, 100, 100.0),
)


class EffectsPanel(QWidget):
    """Master video look controls; all outputs render the same settings."""

    manual_parameter_changed = Signal(str)

    def __init__(self, settings: EffectSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._sliders: dict[str, tuple[QSlider, QLabel, float]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("LOOK"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS) + ["Custom"])
        preset_row.addWidget(self.preset_combo, 1)
        self.reset_button = QPushButton("RESET")
        preset_row.addWidget(self.reset_button)
        root.addLayout(preset_row)

        self.enabled_check = QCheckBox("ENABLE MASTER EFFECTS")
        self.enabled_check.setChecked(settings.enabled)
        root.addWidget(self.enabled_check)

        group = QGroupBox("MASTER FILTERS + OVERLAYS")
        form = QFormLayout(group)
        for key, title, low, high, scale in _SLIDERS:
            row = QHBoxLayout()
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(low, high)
            value_label = QLabel("0")
            value_label.setMinimumWidth(42)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            slider.valueChanged.connect(
                lambda value, field=key, multiplier=scale, label=value_label:
                self._value_changed(field, value, multiplier, label)
            )
            row.addWidget(slider, 1)
            row.addWidget(value_label)
            form.addRow(title, row)
            self._sliders[key] = (slider, value_label, scale)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(group)
        root.addWidget(scroll, 1)

        self.preset_combo.currentTextChanged.connect(self._preset_changed)
        self.enabled_check.toggled.connect(self._enabled_changed)
        self.reset_button.clicked.connect(self._reset)
        self.sync_from_settings()

    def _preset_changed(self, name: str) -> None:
        if name == "Custom":
            return
        self.settings.apply_preset(name)
        self.sync_from_settings()
        self.manual_parameter_changed.emit("master.*")

    def _enabled_changed(self, enabled: bool) -> None:
        self.settings.enabled = bool(enabled)

    def _value_changed(
            self,
            field: str,
            value: int,
            scale: float,
            label: QLabel,
    ) -> None:
        setattr(self.settings, field, value / scale)
        self.manual_parameter_changed.emit(f"master.{field}")
        if not self.settings.enabled:
            self.settings.enabled = True
            self.enabled_check.blockSignals(True)
            self.enabled_check.setChecked(True)
            self.enabled_check.blockSignals(False)
        label.setText(f"{value / scale:.2f}".rstrip("0").rstrip("."))
        if self.preset_combo.currentText() != "Custom":
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentText("Custom")
            self.preset_combo.blockSignals(False)
            self.settings.preset_name = "Custom"

    def _reset(self) -> None:
        self.settings.reset()
        self.sync_from_settings()
        self.manual_parameter_changed.emit("master.*")

    def sync_from_settings(self) -> None:
        self.preset_combo.blockSignals(True)
        name = self.settings.preset_name
        self.preset_combo.setCurrentText(name if name in PRESETS else "Custom")
        self.preset_combo.blockSignals(False)
        self.enabled_check.blockSignals(True)
        self.enabled_check.setChecked(self.settings.enabled)
        self.enabled_check.blockSignals(False)
        for key, (slider, label, scale) in self._sliders.items():
            slider.blockSignals(True)
            value = round(float(getattr(self.settings, key)) * scale)
            slider.setValue(value)
            slider.blockSignals(False)
            label.setText(f"{value / scale:.2f}".rstrip("0").rstrip("."))
