from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.application import Application
from generators.catalog import normalize_settings


class GeneratorsPanel(QWidget):
    """Create and edit transparent procedural and typographic composition layers."""

    composition_changed = Signal()

    def __init__(self, application: Application, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(7)

        add_group = QGroupBox("ADD GENERATOR LAYER")
        add_layout = QVBoxLayout(add_group)
        row_one = QHBoxLayout()
        self.add_geometry_button = QPushButton("+ GEOMETRY")
        self.add_text_button = QPushButton("+ TEXT ART")
        row_one.addWidget(self.add_geometry_button)
        row_one.addWidget(self.add_text_button)
        row_two = QHBoxLayout()
        self.add_waveform_button = QPushButton("+ WAVEFORM")
        self.remove_button = QPushButton("REMOVE SELECTED")
        row_two.addWidget(self.add_waveform_button)
        row_two.addWidget(self.remove_button)
        add_layout.addLayout(row_one)
        add_layout.addLayout(row_two)
        root.addWidget(add_group)

        self.layer_combo = QComboBox()
        root.addWidget(QLabel("SELECTED GENERATOR"))
        root.addWidget(self.layer_combo)

        content_group = QGroupBox("GENERATOR CONTENT")
        content_form = QFormLayout(content_group)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setMaximumBlockCount(32)
        self.text_edit.setFixedHeight(104)
        content_form.addRow("TEXT", self.text_edit)

        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(
            [
                "rings", "grid", "radial", "crosshatch", "polygon",
                "sine", "lissajous", "orbit",
            ]
        )
        content_form.addRow("PATTERN", self.pattern_combo)

        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        families = sorted(set(QFontDatabase.families()), key=str.casefold)
        self.font_combo.addItems(families[:250])
        content_form.addRow("TYPEFACE", self.font_combo)

        self.weight_combo = QComboBox()
        for label, value in (
                ("Regular", 400),
                ("Medium", 500),
                ("Bold", 700),
                ("Black", 900),
        ):
            self.weight_combo.addItem(label, value)
        content_form.addRow("WEIGHT", self.weight_combo)

        self.alignment_combo = QComboBox()
        self.alignment_combo.addItems(["left", "center", "right"])
        content_form.addRow("ALIGNMENT", self.alignment_combo)

        self.vertical_alignment_combo = QComboBox()
        self.vertical_alignment_combo.addItems(["top", "middle", "bottom"])
        content_form.addRow("VERTICAL ALIGNMENT", self.vertical_alignment_combo)

        self.size_slider, self.size_value = self._slider(
            content_form, "FONT SIZE", 12, 420, 148
        )
        self.tracking_slider, self.tracking_value = self._slider(
            content_form, "LETTER TRACKING", -8, 48, 10
        )
        self.line_spacing_slider, self.line_spacing_value = self._slider(
            content_form, "LINE SPACING", 50, 250, 100
        )
        self.density_slider, self.density_value = self._slider(
            content_form, "DENSITY", 1, 80, 12
        )
        self.width_slider, self.width_value = self._slider(
            content_form, "LINE / STROKE", 1, 48, 4
        )
        self.amplitude_slider, self.amplitude_value = self._slider(
            content_form, "WAVE AMPLITUDE", 1, 48, 22
        )
        self.frequency_slider, self.frequency_value = self._slider(
            content_form, "WAVE FREQUENCY", 1, 240, 25
        )
        self.shadow_check = QCheckBox("Soft offset shadow")
        self.shadow_check.setChecked(True)
        content_form.addRow("TEXT SHADOW", self.shadow_check)
        root.addWidget(content_group)

        style_group = QGroupBox("COLOUR AND ANIMATION")
        style_form = QFormLayout(style_group)
        self.primary_color = QLineEdit("#E8E4DA")
        self.secondary_color = QLineEdit("#8678A8")
        self.stroke_color = QLineEdit("#211B2A")
        style_form.addRow("PRIMARY COLOUR", self.primary_color)
        style_form.addRow("ACCENT COLOUR", self.secondary_color)
        style_form.addRow("TEXT OUTLINE", self.stroke_color)

        self.animation_combo = QComboBox()
        self.animation_combo.addItems(["none", "pulse", "rotate", "drift", "flicker"])
        style_form.addRow("ANIMATION", self.animation_combo)
        self.speed_slider, self.speed_value = self._slider(
            style_form, "ANIMATION SPEED", 0, 800, 18
        )
        self.amount_slider, self.amount_value = self._slider(
            style_form, "ANIMATION AMOUNT", 0, 100, 30
        )
        root.addWidget(style_group)

        self.apply_button = QPushButton("APPLY TO SELECTED LAYER")
        self.apply_button.setDefault(True)
        root.addWidget(self.apply_button)
        self.hint_label = QLabel(
            "Generator layers are transparent and render in both the preview "
            "and projector output."
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("mutedLabel")
        root.addWidget(self.hint_label)
        root.addStretch(1)

        self.add_geometry_button.clicked.connect(lambda: self.add_generator("geometry"))
        self.add_text_button.clicked.connect(lambda: self.add_generator("text"))
        self.add_waveform_button.clicked.connect(lambda: self.add_generator("waveform"))
        self.remove_button.clicked.connect(self.remove_selected)
        self.layer_combo.currentIndexChanged.connect(self.load_selected)
        self.apply_button.clicked.connect(self.apply_settings)
        self.refresh()

    @staticmethod
    def _slider(
            form: QFormLayout,
            title: str,
            minimum: int,
            maximum: int,
            default: int,
    ) -> tuple[QSlider, QLabel]:
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(default)
        value_label = QLabel(str(default))
        value_label.setMinimumWidth(34)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        slider.valueChanged.connect(lambda value: value_label.setText(str(value)))
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        form.addRow(title, row)
        return slider, value_label

    def _selected_layer(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            return None
        layer = self.application.composition.get_layer(str(layer_id))
        if layer is None or layer.source_type != "generator":
            return None
        return layer

    def add_generator(self, generator_type: str) -> None:
        layer = self.application.add_generator_layer(generator_type)
        self.refresh(select_id=layer.id)
        self.composition_changed.emit()

    def refresh(self, select_id: str | None = None) -> None:
        previous = select_id or self.layer_combo.currentData()
        layers = [
            layer for layer in self.application.composition.layers
            if layer.source_type == "generator"
        ]
        self._loading = True
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        labels = {
            "geometry": "GEOMETRY",
            "text": "TEXT ART",
            "waveform": "WAVEFORM",
        }
        for layer in layers:
            label = f"{labels.get(layer.generator_type, 'GENERATOR')} · {layer.name}"
            self.layer_combo.addItem(label, layer.id)
        selected = self.layer_combo.findData(previous)
        self.layer_combo.setCurrentIndex(selected if selected >= 0 else 0)
        self.layer_combo.blockSignals(False)
        self._loading = False
        self.load_selected()

    def load_selected(self, *_args) -> None:
        layer = self._selected_layer()
        enabled = layer is not None
        for widget in (
                self.text_edit,
                self.pattern_combo,
                self.font_combo,
                self.weight_combo,
                self.alignment_combo,
                self.vertical_alignment_combo,
                self.size_slider,
                self.tracking_slider,
                self.line_spacing_slider,
                self.shadow_check,
                self.density_slider,
                self.width_slider,
                self.amplitude_slider,
                self.frequency_slider,
                self.primary_color,
                self.secondary_color,
                self.stroke_color,
                self.animation_combo,
                self.speed_slider,
                self.amount_slider,
                self.apply_button,
                self.remove_button,
        ):
            widget.setEnabled(enabled)
        if not enabled or self._loading:
            return

        values = normalize_settings(
            layer.generator_type or "geometry",
            layer.generator_settings,
        )
        self._loading = True
        self.text_edit.setPlainText(str(values.get("text", "")))
        self.pattern_combo.setCurrentText(str(values.get("pattern", "rings")))
        self.font_combo.setCurrentText(str(values.get("font_family", "Arial")))
        weight_index = self.weight_combo.findData(int(values.get("font_weight", 700)))
        self.weight_combo.setCurrentIndex(max(0, weight_index))
        self.alignment_combo.setCurrentText(str(values.get("alignment", "center")))
        self.vertical_alignment_combo.setCurrentText(
            str(values.get("vertical_alignment", "middle"))
        )
        self.size_slider.setValue(int(values.get("font_size", 148)))
        self.tracking_slider.setValue(round(float(values.get("letter_spacing", 10.0))))
        self.line_spacing_slider.setValue(round(
            float(values.get("line_spacing", 1.0)) * 100
        ))
        self.shadow_check.setChecked(bool(values.get("shadow", True)))
        self.density_slider.setValue(int(values.get("density", 12)))
        self.width_slider.setValue(round(float(
            values.get("stroke_width", values.get("line_width", 2.0))
        ) * 2))
        self.amplitude_slider.setValue(round(float(values.get("amplitude", 0.22)) * 100))
        self.frequency_slider.setValue(round(float(values.get("frequency", 2.5)) * 10))
        self.primary_color.setText(str(values.get("primary_color", "#E8E4DA")))
        self.secondary_color.setText(str(values.get("secondary_color", "#8678A8")))
        self.stroke_color.setText(str(values.get("stroke_color", "#211B2A")))
        self.animation_combo.setCurrentText(str(values.get("animation", "none")))
        self.speed_slider.setValue(round(float(values.get("animation_speed", 0.18)) * 100))
        amount = float(values.get("animation_amount", 0.0))
        if values.get("animation") == "rotate":
            amount_value = round(min(100.0, amount / 3.6))
        else:
            amount_value = round(min(100.0, amount / 0.45 * 100.0))
        self.amount_slider.setValue(amount_value)
        self._loading = False

    def apply_settings(self) -> None:
        layer = self._selected_layer()
        if layer is None:
            return
        settings = dict(layer.generator_settings)
        generator_type = layer.generator_type or "geometry"
        settings.update({
            "primary_color": self.primary_color.text().strip() or "#E8E4DA",
            "secondary_color": self.secondary_color.text().strip() or "#8678A8",
            "animation": self.animation_combo.currentText(),
            "animation_speed": self.speed_slider.value() / 100.0,
        })
        animation_amount = self.amount_slider.value() / 100.0
        settings["animation_amount"] = (
            animation_amount * 3.6
            if settings["animation"] == "rotate"
            else animation_amount * 0.45
        )

        if generator_type == "geometry":
            settings.update({
                "pattern": self.pattern_combo.currentText(),
                "density": self.density_slider.value(),
                "line_width": self.width_slider.value() / 2.0,
            })
        elif generator_type == "text":
            settings.update({
                "text": self.text_edit.toPlainText(),
                "font_family": self.font_combo.currentText().strip() or "Arial",
                "font_size": self.size_slider.value(),
                "font_weight": int(self.weight_combo.currentData()),
                "letter_spacing": float(self.tracking_slider.value()),
                "line_spacing": self.line_spacing_slider.value() / 100.0,
                "alignment": self.alignment_combo.currentText(),
                "vertical_alignment": self.vertical_alignment_combo.currentText(),
                "shadow": self.shadow_check.isChecked(),
                "stroke_color": self.stroke_color.text().strip() or "#211B2A",
                "stroke_width": self.width_slider.value() / 2.0,
            })
        elif generator_type == "waveform":
            settings.update({
                "pattern": self.pattern_combo.currentText(),
                "density": self.density_slider.value(),
                "line_width": self.width_slider.value() / 2.0,
                "amplitude": self.amplitude_slider.value() / 100.0,
                "frequency": self.frequency_slider.value() / 10.0,
            })

        normalized = normalize_settings(generator_type, settings)
        self.application.layer_manager.update_layer(
            layer.id,
            generator_settings=normalized,
        )
        self.hint_label.setText(
            f"Applied {layer.name}. The raster texture updates once; animation remains GPU-side."
        )

    def remove_selected(self) -> None:
        layer = self._selected_layer()
        if layer is None:
            return
        self.application.remove_layer(layer.id)
        self.refresh()
        self.composition_changed.emit()
