from __future__ import annotations

import random

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.application import Application
from generators.catalog import normalize_settings
from generators.text_pools import random_text_sample


class GeneratorsPanel(QWidget):
    """Create and edit transparent procedural and typographic composition layers."""

    composition_changed = Signal()

    def __init__(self, application: Application, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        self._loading = False
        self.setMinimumWidth(320)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setObjectName("generatorSettingsScroll")
        body = QWidget()
        root = QVBoxLayout(body)
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
        self.add_particles_button = QPushButton("+ PARTICLES")
        row_two.addWidget(self.add_waveform_button)
        row_two.addWidget(self.add_particles_button)
        row_three = QHBoxLayout()
        self.add_overlay_button = QPushButton("+ IMAGE / VIDEO OVERLAY")
        self.remove_button = QPushButton("REMOVE SELECTED")
        row_three.addWidget(self.add_overlay_button)
        row_three.addWidget(self.remove_button)
        add_layout.addLayout(row_one)
        add_layout.addLayout(row_two)
        add_layout.addLayout(row_three)
        root.addWidget(add_group)

        root.addWidget(QLabel("SELECTED GENERATOR"))
        self.layer_combo = QComboBox()
        root.addWidget(self.layer_combo)

        self.text_group = QGroupBox("TEXT ART")
        text_form = QFormLayout(self.text_group)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setMaximumBlockCount(32)
        self.text_edit.setFixedHeight(100)
        text_form.addRow("CONTENT", self.text_edit)

        self.text_layout_combo = QComboBox()
        self.text_layout_combo.addItem("Single text block", "single")
        self.text_layout_combo.addItem("Typographic word collage", "collage")
        text_form.addRow("LAYOUT", self.text_layout_combo)

        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        families = sorted(set(QFontDatabase.families()), key=str.casefold)
        self.font_combo.addItems(families[:250])
        text_form.addRow("TYPEFACE", self.font_combo)

        self.weight_combo = QComboBox()
        for label, value in (
                ("Regular", 400),
                ("Medium", 500),
                ("Bold", 700),
                ("Black", 900),
        ):
            self.weight_combo.addItem(label, value)
        text_form.addRow("WEIGHT", self.weight_combo)

        self.text_color_mode_combo = QComboBox()
        self.text_color_mode_combo.addItem("Single colour", "single")
        self.text_color_mode_combo.addItem("Alternate line colours", "alternate")
        text_form.addRow("COLOUR MODE", self.text_color_mode_combo)

        self.text_size_slider, self.text_size_value = self._slider(
            text_form, "FONT SIZE", 12, 420, 148
        )
        self.tracking_slider, self.tracking_value = self._slider(
            text_form, "LETTER TRACKING", -8, 48, 10
        )
        self.line_spacing_slider, self.line_spacing_value = self._slider(
            text_form, "LINE SPACING", 50, 250, 100
        )

        self.alignment_combo = QComboBox()
        self.alignment_combo.addItems(["left", "center", "right"])
        text_form.addRow("ALIGNMENT", self.alignment_combo)

        self.vertical_alignment_combo = QComboBox()
        self.vertical_alignment_combo.addItems(["top", "middle", "bottom"])
        text_form.addRow("VERTICAL ALIGNMENT", self.vertical_alignment_combo)

        self.stroke_color = QLineEdit("#211B2A")
        text_form.addRow("OUTLINE COLOUR", self.stroke_color)
        self.text_outline_slider, self.text_outline_value = self._slider(
            text_form, "OUTLINE WIDTH", 0, 48, 4
        )
        self.shadow_check = QCheckBox("Soft offset shadow")
        self.shadow_check.setChecked(True)
        text_form.addRow("SHADOW", self.shadow_check)

        self.collage_variation_slider, self.collage_variation_value = self._slider(
            text_form, "COLLAGE VARIATION", 0, 100, 65
        )
        self.text_animation_combo = QComboBox()
        self.text_animation_combo.addItem("None", "none")
        self.text_animation_combo.addItem("Type-on", "type_on")
        self.text_animation_combo.addItem("Word / column reveal", "word_reveal")
        self.text_animation_combo.addItem("Line wave", "line_wave")
        self.text_animation_combo.addItem("Glyph jitter", "jitter")
        self.text_animation_combo.addItem("Crawl", "crawl")
        self.text_animation_combo.addItem("Signal glitch", "glitch")
        text_form.addRow("TEXT MOTION", self.text_animation_combo)
        self.text_animation_speed_slider, self.text_animation_speed_value = self._slider(
            text_form, "MOTION SPEED", 0, 800, 100
        )
        self.text_animation_amount_slider, self.text_animation_amount_value = self._slider(
            text_form, "MOTION AMOUNT", 0, 180, 25
        )
        self.text_animation_columns_slider, self.text_animation_columns_value = self._slider(
            text_form, "REVEAL STEPS", 2, 80, 18
        )

        random_group = QGroupBox("RANDOM TEXT POOL · ENGLISH / 日本語")
        random_form = QFormLayout(random_group)
        self.random_language_combo = QComboBox()
        self.random_language_combo.addItem("Bilingual", "bilingual")
        self.random_language_combo.addItem("English", "english")
        self.random_language_combo.addItem("日本語", "japanese")
        random_form.addRow("LANGUAGE", self.random_language_combo)
        self.random_theme_combo = QComboBox()
        for label, value in (
            ("Random mix", "random"),
            ("Memory / 記憶", "memory"),
            ("Body / 身体", "body"),
            ("Signal / 信号", "signal"),
            ("Ritual / 儀式", "ritual"),
            ("Identity / 自己", "identity"),
        ):
            self.random_theme_combo.addItem(label, value)
        random_form.addRow("THEME", self.random_theme_combo)
        self.random_count_combo = QComboBox()
        for count in (8, 12, 16, 20, 24, 32):
            self.random_count_combo.addItem(str(count), count)
        self.random_count_combo.setCurrentText("16")
        random_form.addRow("FRAGMENTS", self.random_count_combo)
        self.random_text_button = QPushButton("GENERATE RANDOM TEXT COLLAGE")
        random_form.addRow(self.random_text_button)
        text_form.addRow(random_group)
        root.addWidget(self.text_group)

        self.geometry_group = QGroupBox("GEOMETRY PATTERN")
        geometry_form = QFormLayout(self.geometry_group)
        self.geometry_pattern_combo = QComboBox()
        self.geometry_pattern_combo.addItems(
            ["rings", "grid", "radial", "crosshatch", "polygon", "spiral", "moire", "hexgrid"]
        )
        geometry_form.addRow("PATTERN", self.geometry_pattern_combo)
        self.geometry_density_slider, self.geometry_density_value = self._slider(
            geometry_form, "DENSITY", 2, 80, 12
        )
        self.geometry_width_slider, self.geometry_width_value = self._slider(
            geometry_form, "LINE WIDTH", 1, 48, 4
        )
        root.addWidget(self.geometry_group)

        self.waveform_group = QGroupBox("WAVEFORM")
        waveform_form = QFormLayout(self.waveform_group)
        self.waveform_pattern_combo = QComboBox()
        self.waveform_pattern_combo.addItems(
            ["sine", "lissajous", "orbit", "radial", "rose"]
        )
        waveform_form.addRow("PATTERN", self.waveform_pattern_combo)
        self.waveform_density_slider, self.waveform_density_value = self._slider(
            waveform_form, "TRACES", 1, 12, 5
        )
        self.waveform_width_slider, self.waveform_width_value = self._slider(
            waveform_form, "LINE WIDTH", 1, 40, 6
        )
        self.amplitude_slider, self.amplitude_value = self._slider(
            waveform_form, "AMPLITUDE", 1, 48, 22
        )
        self.frequency_slider, self.frequency_value = self._slider(
            waveform_form, "FREQUENCY", 1, 240, 25
        )
        root.addWidget(self.waveform_group)

        self.particles_group = QGroupBox("GPU PARTICLE FIELD")
        particles_form = QFormLayout(self.particles_group)
        self.particle_density_slider, self.particle_density_value = self._slider(
            particles_form, "PARTICLE COUNT", 4, 120, 42
        )
        self.particle_speed_slider, self.particle_speed_value = self._slider(
            particles_form, "SPEED", 0, 200, 22
        )
        self.particle_size_slider, self.particle_size_value = self._slider(
            particles_form, "SIZE", 2, 80, 18
        )
        self.particle_spread_slider, self.particle_spread_value = self._slider(
            particles_form, "DRIFT / SPREAD", 0, 100, 42
        )
        self.particle_trail_slider, self.particle_trail_value = self._slider(
            particles_form, "TRAIL", 0, 100, 18
        )
        self.particle_mode_combo = QComboBox()
        self.particle_mode_combo.addItems(["drift", "rise", "fall", "orbit"])
        particles_form.addRow("EMITTER MODE", self.particle_mode_combo)
        root.addWidget(self.particles_group)

        self.style_group = QGroupBox("COLOUR AND ANIMATION")
        style_form = QFormLayout(self.style_group)
        self.primary_color = QLineEdit("#E8E4DA")
        self.secondary_color = QLineEdit("#8678A8")
        style_form.addRow("PRIMARY COLOUR", self.primary_color)
        style_form.addRow("ACCENT COLOUR", self.secondary_color)

        self.animation_combo = QComboBox()
        self.animation_combo.addItems(["none", "pulse", "rotate", "drift", "flicker"])
        style_form.addRow("ANIMATION", self.animation_combo)
        self.speed_slider, self.speed_value = self._slider(
            style_form, "ANIMATION SPEED", 0, 800, 18
        )
        self.amount_slider, self.amount_value = self._slider(
            style_form, "ANIMATION AMOUNT", 0, 100, 30
        )
        root.addWidget(self.style_group)

        self.apply_button = QPushButton("APPLY TO SELECTED LAYER")
        self.apply_button.setDefault(True)
        root.addWidget(self.apply_button)
        self.hint_label = QLabel(
            "Generator content is saved with the composition and rendered by the preview "
            "and projector outputs."
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("mutedLabel")
        root.addWidget(self.hint_label)
        root.addStretch(1)

        self.scroll.setWidget(body)
        outer.addWidget(self.scroll)

        self.add_geometry_button.clicked.connect(lambda: self.add_generator("geometry"))
        self.add_text_button.clicked.connect(lambda: self.add_generator("text"))
        self.add_waveform_button.clicked.connect(lambda: self.add_generator("waveform"))
        self.add_particles_button.clicked.connect(lambda: self.add_generator("particles"))
        self.add_overlay_button.clicked.connect(self.add_overlay_media)
        self.remove_button.clicked.connect(self.remove_selected)
        self.layer_combo.currentIndexChanged.connect(self.load_selected)
        self.apply_button.clicked.connect(self.apply_settings)
        self.random_text_button.clicked.connect(self.randomize_text)
        self._collage_seed = 211
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(150)
        self._apply_timer.timeout.connect(self.apply_settings)
        self._connect_live_updates()
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

    def _connect_live_updates(self) -> None:
        for widget in (
            self.text_edit,
            self.font_combo,
            self.weight_combo,
            self.text_color_mode_combo,
            self.text_layout_combo,
            self.alignment_combo,
            self.vertical_alignment_combo,
            self.stroke_color,
            self.primary_color,
            self.secondary_color,
            self.animation_combo,
            self.text_animation_combo,
            self.geometry_pattern_combo,
            self.waveform_pattern_combo,
            self.particle_mode_combo,
            self.random_language_combo,
            self.random_theme_combo,
            self.random_count_combo,
        ):
            signal = getattr(widget, "textChanged", None)
            if signal is None:
                signal = getattr(widget, "currentTextChanged", None)
            if signal is not None:
                signal.connect(self._schedule_apply)
        for slider in (
            self.text_size_slider,
            self.tracking_slider,
            self.line_spacing_slider,
            self.text_outline_slider,
            self.collage_variation_slider,
            self.text_animation_speed_slider,
            self.text_animation_amount_slider,
            self.text_animation_columns_slider,
            self.geometry_density_slider,
            self.geometry_width_slider,
            self.waveform_density_slider,
            self.waveform_width_slider,
            self.amplitude_slider,
            self.frequency_slider,
            self.particle_density_slider,
            self.particle_speed_slider,
            self.particle_size_slider,
            self.particle_spread_slider,
            self.particle_trail_slider,
            self.speed_slider,
            self.amount_slider,
        ):
            slider.valueChanged.connect(self._schedule_apply)
        self.shadow_check.toggled.connect(self._schedule_apply)

    def _schedule_apply(self, *_args) -> None:
        if self._loading or self._selected_layer() is None:
            return
        self._apply_timer.start()

    def randomize_text(self) -> None:
        language = str(self.random_language_combo.currentData())
        theme = str(self.random_theme_combo.currentData())
        count = int(self.random_count_combo.currentData())
        self._collage_seed = random.randrange(0, 2**31 - 1)
        self.text_edit.setPlainText(
            random_text_sample(language, theme, count, self._collage_seed)
        )
        self.text_layout_combo.setCurrentIndex(
            max(0, self.text_layout_combo.findData("collage"))
        )
        self.text_color_mode_combo.setCurrentIndex(
            max(0, self.text_color_mode_combo.findData("alternate"))
        )
        self._schedule_apply()

    def add_overlay_media(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Add image or video overlay",
            "",
            (
                "Overlay media (*.png *.apng *.gif *.webp *.jpg *.jpeg *.bmp "
                "*.mp4 *.mov *.mkv *.avi *.webm *.m4v);;"
                "Images (*.png *.apng *.gif *.webp *.jpg *.jpeg *.bmp);;"
                "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)"
            ),
        )
        if not path:
            return
        try:
            layer = self.application.add_media_overlay(path)
            self.hint_label.setText(
                f"Added overlay {layer.name}. It is now a normal composition layer."
            )
            self.composition_changed.emit()
        except Exception as exc:
            self.hint_label.setText(f"Could not add overlay: {exc}")

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
        labels = {
            "geometry": "GEOMETRY",
            "text": "TEXT ART",
            "waveform": "WAVEFORM",
            "particles": "PARTICLES",
        }
        self._loading = True
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
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
        generator_type = layer.generator_type if layer else None

        self.text_group.setVisible(generator_type == "text")
        self.geometry_group.setVisible(generator_type == "geometry")
        self.waveform_group.setVisible(generator_type == "waveform")
        self.particles_group.setVisible(generator_type == "particles")
        self.style_group.setVisible(enabled)
        self.apply_button.setEnabled(enabled and not layer.locked if layer else False)
        self.remove_button.setEnabled(enabled)
        if not enabled or self._loading:
            return

        values = normalize_settings(generator_type or "geometry", layer.generator_settings)
        self._loading = True

        if generator_type == "text":
            self.text_edit.setPlainText(str(values["text"]))
            self.text_layout_combo.setCurrentIndex(
                max(0, self.text_layout_combo.findData(values["text_layout"]))
            )
            self._collage_seed = int(values["collage_seed"])
            self.collage_variation_slider.setValue(
                round(float(values["collage_font_variation"]) * 100)
            )
            self.text_animation_combo.setCurrentIndex(
                max(0, self.text_animation_combo.findData(values["text_animation"]))
            )
            self.text_animation_speed_slider.setValue(
                round(float(values["text_animation_speed"]) * 100)
            )
            self.text_animation_amount_slider.setValue(
                round(float(values["text_animation_amount"]) * 1000)
            )
            self.text_animation_columns_slider.setValue(
                int(values["text_animation_columns"])
            )
            self.font_combo.setCurrentText(str(values["font_family"]))
            weight_index = self.weight_combo.findData(int(values["font_weight"]))
            self.weight_combo.setCurrentIndex(max(0, weight_index))
            self.text_color_mode_combo.setCurrentIndex(
                max(0, self.text_color_mode_combo.findData(values["text_color_mode"]))
            )
            self.text_size_slider.setValue(int(values["font_size"]))
            self.tracking_slider.setValue(round(float(values["letter_spacing"])))
            self.line_spacing_slider.setValue(round(float(values["line_spacing"]) * 100))
            self.alignment_combo.setCurrentText(str(values["alignment"]))
            self.vertical_alignment_combo.setCurrentText(str(values["vertical_alignment"]))
            self.stroke_color.setText(str(values["stroke_color"]))
            self.text_outline_slider.setValue(round(float(values["stroke_width"]) * 2))
            self.shadow_check.setChecked(bool(values["shadow"]))
        elif generator_type == "geometry":
            self.geometry_pattern_combo.setCurrentText(str(values["pattern"]))
            self.geometry_density_slider.setValue(int(values["density"]))
            self.geometry_width_slider.setValue(round(float(values["line_width"]) * 2))
        elif generator_type == "waveform":
            self.waveform_pattern_combo.setCurrentText(str(values["pattern"]))
            self.waveform_density_slider.setValue(int(values["density"]))
            self.waveform_width_slider.setValue(round(float(values["line_width"]) * 2))
            self.amplitude_slider.setValue(round(float(values["amplitude"]) * 100))
            self.frequency_slider.setValue(round(float(values["frequency"]) * 10))
        elif generator_type == "particles":
            self.particle_density_slider.setValue(int(values["density"]))
            self.particle_speed_slider.setValue(round(float(values["speed"]) * 100))
            self.particle_size_slider.setValue(round(float(values["size"]) * 100))
            self.particle_spread_slider.setValue(round(float(values["spread"]) * 100))
            self.particle_trail_slider.setValue(round(float(values["trail"]) * 100))
            self.particle_mode_combo.setCurrentText(str(values["mode"]))

        self.primary_color.setText(str(values["primary_color"]))
        self.secondary_color.setText(str(values.get("secondary_color", "#C35C75")))
        self.animation_combo.setCurrentText(str(values["animation"]))
        self.speed_slider.setValue(round(float(values["animation_speed"]) * 100))
        amount = float(values["animation_amount"])
        if values["animation"] == "rotate":
            amount_value = round(min(100.0, amount / 3.6))
        else:
            amount_value = round(min(100.0, amount / 0.45 * 100.0))
        self.amount_slider.setValue(amount_value)
        self._loading = False

    def apply_settings(self) -> None:
        layer = self._selected_layer()
        if layer is None or layer.locked:
            return

        generator_type = layer.generator_type or "geometry"
        settings = dict(layer.generator_settings)
        settings.update({
            "primary_color": self.primary_color.text().strip() or "#E8E4DA",
            "secondary_color": self.secondary_color.text().strip() or "#8678A8",
            "animation": self.animation_combo.currentText(),
            "animation_speed": self.speed_slider.value() / 100.0,
        })
        amount = self.amount_slider.value() / 100.0
        settings["animation_amount"] = (
            amount * 3.6 if settings["animation"] == "rotate" else amount * 0.45
        )

        if generator_type == "text":
            settings.update({
                "text": self.text_edit.toPlainText(),
                "text_layout": str(self.text_layout_combo.currentData()),
                "collage_seed": self._collage_seed,
                "collage_font_variation": self.collage_variation_slider.value() / 100.0,
                "text_animation": str(self.text_animation_combo.currentData()),
                "text_animation_speed": self.text_animation_speed_slider.value() / 100.0,
                "text_animation_amount": (
                    self.text_animation_amount_slider.value() / 1000.0
                ),
                "text_animation_columns": self.text_animation_columns_slider.value(),
                "font_family": self.font_combo.currentText().strip() or "Arial",
                "font_size": self.text_size_slider.value(),
                "font_weight": int(self.weight_combo.currentData()),
                "text_color_mode": str(self.text_color_mode_combo.currentData()),
                "letter_spacing": float(self.tracking_slider.value()),
                "line_spacing": self.line_spacing_slider.value() / 100.0,
                "alignment": self.alignment_combo.currentText(),
                "vertical_alignment": self.vertical_alignment_combo.currentText(),
                "stroke_color": self.stroke_color.text().strip() or "#211B2A",
                "stroke_width": self.text_outline_slider.value() / 2.0,
                "shadow": self.shadow_check.isChecked(),
            })
        elif generator_type == "geometry":
            settings.update({
                "pattern": self.geometry_pattern_combo.currentText(),
                "density": self.geometry_density_slider.value(),
                "line_width": self.geometry_width_slider.value() / 2.0,
            })
        elif generator_type == "waveform":
            settings.update({
                "pattern": self.waveform_pattern_combo.currentText(),
                "density": self.waveform_density_slider.value(),
                "line_width": self.waveform_width_slider.value() / 2.0,
                "amplitude": self.amplitude_slider.value() / 100.0,
                "frequency": self.frequency_slider.value() / 10.0,
            })

        elif generator_type == "particles":
            settings.update({
                "density": self.particle_density_slider.value(),
                "speed": self.particle_speed_slider.value() / 100.0,
                "size": self.particle_size_slider.value() / 100.0,
                "spread": self.particle_spread_slider.value() / 100.0,
                "trail": self.particle_trail_slider.value() / 100.0,
                "mode": self.particle_mode_combo.currentText(),
            })

        normalized = normalize_settings(generator_type, settings)
        self.application.layer_manager.update_layer(
            layer.id,
            generator_settings=normalized,
        )
        self.hint_label.setText(
            f"Applied {layer.name}. Static content updates once; animation remains GPU-side."
        )

    def remove_selected(self) -> None:
        layer = self._selected_layer()
        if layer is None:
            return
        self.application.remove_layer(layer.id)
        self.refresh()
        self.composition_changed.emit()
