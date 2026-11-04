from __future__ import annotations

import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.application import Application
from effects.layer_settings import (
    LAYER_EFFECT_PRESETS,
    EFFECT_STAGE_TYPES,
    normalize_layer_effects,
)

_BLEND_MODES = ("normal", "add", "screen", "multiply", "difference")


class LayerPanel(QWidget):
    layers_changed = Signal()

    def __init__(self, application: Application, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Visible", "Layer", "Opacity", "Blend"])
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._visibility_changed)
        self.table.currentCellChanged.connect(self._selection_changed)
        layout.addWidget(self.table, 1)

        controls_body = QWidget()
        controls_layout = QVBoxLayout(controls_body)
        controls_layout.setContentsMargins(2, 2, 2, 2)

        transform_group = QGroupBox("SELECTED LAYER TRANSFORM")
        transform_layout = QVBoxLayout(transform_group)
        self.position_x = self._add_slider(transform_layout, "X POSITION", 0, 100, 50)
        self.position_y = self._add_slider(transform_layout, "Y POSITION", 0, 100, 50)
        self.scale = self._add_slider(transform_layout, "UNIFORM SCALE", 10, 200, 100)
        self.rotation = self._add_slider(transform_layout, "ROTATION", -180, 180, 0)
        controls_layout.addWidget(transform_group)

        self.layer_fx_group = QGroupBox("SELECTED LAYER EFFECT STACK")
        layer_fx_layout = QVBoxLayout(self.layer_fx_group)
        self.layer_fx_enabled = QCheckBox("ENABLE LAYER EFFECTS")
        self.layer_fx_layout = layer_fx_layout
        layer_fx_layout.addWidget(self.layer_fx_enabled)
        self.layer_fx_preset = QComboBox()
        self.layer_fx_preset.addItems(list(LAYER_EFFECT_PRESETS) + ["Custom"])
        layer_fx_layout.addWidget(self.layer_fx_preset)
        layer_fx_layout.addWidget(QLabel("STAGE ORDER · TOP TO BOTTOM"))
        self.fx_stage_list = QListWidget()
        self.fx_stage_list.setMaximumHeight(120)
        layer_fx_layout.addWidget(self.fx_stage_list)
        stage_row = QHBoxLayout()
        self.fx_stage_type = QComboBox()
        for key, title in EFFECT_STAGE_TYPES.items():
            self.fx_stage_type.addItem(title, key)
        stage_row.addWidget(self.fx_stage_type, 1)
        self.fx_stage_add = QPushButton("ADD")
        self.fx_stage_remove = QPushButton("REMOVE")
        self.fx_stage_up = QPushButton("↑")
        self.fx_stage_down = QPushButton("↓")
        for button in (self.fx_stage_add, self.fx_stage_remove, self.fx_stage_up, self.fx_stage_down):
            stage_row.addWidget(button)
        layer_fx_layout.addLayout(stage_row)
        chain_row = QHBoxLayout()
        self.fx_chain_save = QPushButton("SAVE CHAIN…")
        self.fx_chain_export = QPushButton("EXPORT PRESETS…")
        self.fx_chain_import = QPushButton("IMPORT PRESETS…")
        for button in (self.fx_chain_save, self.fx_chain_export, self.fx_chain_import):
            chain_row.addWidget(button)
        layer_fx_layout.addLayout(chain_row)
        self.layer_fx_sliders = {}
        for key, title, minimum, maximum, default in (
                ("mix", "FX MIX", 0, 100, 100),
                ("monochrome", "MONOCHROME", 0, 100, 0),
                ("invert", "INVERT", 0, 100, 0),
                ("threshold", "THRESHOLD", 0, 100, 0),
                ("posterize", "POSTERIZE", 0, 100, 0),
                ("hue", "HUE", -180, 180, 0),
                ("contrast", "CONTRAST", 0, 250, 100),
                ("saturation", "SATURATION", 0, 250, 100),
                ("brightness", "BRIGHTNESS", -50, 50, 0),
                ("scanlines", "SCANLINES", 0, 100, 0),
                ("chromatic", "RGB SPLIT", 0, 100, 0),
        ):
            label, slider = self._add_fx_slider(
                layer_fx_layout,
                title,
                minimum,
                maximum,
                default,
            )
            self.layer_fx_sliders[key] = (label, slider, title)
        controls_layout.addWidget(self.layer_fx_group)

        self.remove_layer_button = QPushButton("REMOVE SELECTED LAYER")
        controls_layout.addWidget(self.remove_layer_button)
        controls_layout.addStretch(1)
        self.controls_scroll = QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.controls_scroll.setWidget(controls_body)
        layout.addWidget(self.controls_scroll, 1)

        self.position_x[1].valueChanged.connect(self._position_x_changed)
        self.position_y[1].valueChanged.connect(self._position_y_changed)
        self.scale[1].valueChanged.connect(self._scale_changed)
        self.rotation[1].valueChanged.connect(self._rotation_changed)
        self.layer_fx_enabled.toggled.connect(self._layer_fx_enabled_changed)
        self.layer_fx_preset.currentTextChanged.connect(self._layer_fx_preset_changed)
        self.fx_stage_add.clicked.connect(self._add_fx_stage)
        self.fx_stage_remove.clicked.connect(self._remove_fx_stage)
        self.fx_stage_up.clicked.connect(lambda: self._move_fx_stage(-1))
        self.fx_stage_down.clicked.connect(lambda: self._move_fx_stage(1))
        self.fx_chain_save.clicked.connect(self._save_fx_chain)
        self.fx_chain_export.clicked.connect(self._export_fx_presets)
        self.fx_chain_import.clicked.connect(self._import_fx_presets)
        for key, (_label, slider, _title) in self.layer_fx_sliders.items():
            slider.valueChanged.connect(
                lambda value, field=key: self._layer_fx_value_changed(field, value)
            )
        self.remove_layer_button.clicked.connect(self.remove_selected_layer)
        self._loading = False
        self.refresh()

    @staticmethod
    def _add_slider(
            parent_layout: QVBoxLayout,
            title: str,
            minimum: int,
            maximum: int,
            value: int,
    ) -> tuple[QLabel, QSlider]:
        row = QHBoxLayout()
        label = QLabel(f"{title}  {value}")
        label.setMinimumWidth(125)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(lambda current: label.setText(f"{title}  {current}"))
        row.addWidget(label)
        row.addWidget(slider, 1)
        parent_layout.addLayout(row)
        return label, slider

    @staticmethod
    def _add_fx_slider(
            parent_layout: QVBoxLayout,
            title: str,
            minimum: int,
            maximum: int,
            value: int,
    ) -> tuple[QLabel, QSlider]:
        row = QHBoxLayout()
        label = QLabel(f"{title}  {value}")
        label.setMinimumWidth(125)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(lambda current: label.setText(f"{title}  {current}"))
        row.addWidget(label)
        row.addWidget(slider, 1)
        parent_layout.addLayout(row)
        return label, slider

    def refresh(self) -> None:
        selected_id = None
        current = self._selected_layer()
        if current is not None:
            selected_id = current.id
        self._loading = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for layer in self.application.composition.layers:
            row = self.table.rowCount()
            self.table.insertRow(row)

            visible = QTableWidgetItem()
            visible.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            visible.setCheckState(
                Qt.CheckState.Checked if layer.visible else Qt.CheckState.Unchecked
            )
            visible.setData(Qt.ItemDataRole.UserRole, layer.id)
            self.table.setItem(row, 0, visible)

            name = QTableWidgetItem(layer.name)
            name.setData(Qt.ItemDataRole.UserRole, layer.id)
            self.table.setItem(row, 1, name)

            opacity = QSlider(Qt.Orientation.Horizontal)
            opacity.setRange(0, 100)
            opacity.setValue(round(layer.opacity * 100))
            opacity.valueChanged.connect(
                lambda value, layer_id=layer.id: self._opacity_changed(layer_id, value)
            )
            self.table.setCellWidget(row, 2, opacity)

            blend = QComboBox()
            blend.addItems(_BLEND_MODES)
            blend.setCurrentText(layer.blend_mode)
            blend.currentTextChanged.connect(
                lambda value, layer_id=layer.id: self._blend_changed(layer_id, value)
            )
            self.table.setCellWidget(row, 3, blend)
        self.table.blockSignals(False)
        if self.table.rowCount():
            selected_row = 0
            if selected_id:
                for row in range(self.table.rowCount()):
                    if self.table.item(row, 1).data(Qt.ItemDataRole.UserRole) == selected_id:
                        selected_row = row
                        break
            self.table.setCurrentCell(selected_row, 1)
            self._selection_changed(selected_row, 1, -1, -1)
        self._loading = False

    def _selected_layer(self):
        row = self.table.currentRow()
        item = self.table.item(row, 1) if row >= 0 else None
        layer_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        return self.application.composition.get_layer(layer_id) if layer_id else None

    def _selection_changed(
            self,
            current_row: int,
            current_column: int,
            previous_row: int,
            previous_column: int,
    ) -> None:
        layer = self._selected_layer()
        sliders = (self.position_x[1], self.position_y[1], self.scale[1], self.rotation[1])
        for slider in sliders:
            slider.blockSignals(True)
        self.remove_layer_button.setEnabled(layer is not None)
        if layer is None:
            self.layer_fx_group.setEnabled(False)
            self.position_x[1].setEnabled(False)
            self.position_y[1].setEnabled(False)
            self.scale[1].setEnabled(False)
            self.rotation[1].setEnabled(False)
        else:
            self.layer_fx_group.setEnabled(True)
            self.position_x[1].setEnabled(True)
            self.position_y[1].setEnabled(True)
            self.scale[1].setEnabled(True)
            self.rotation[1].setEnabled(True)
            self.position_x[1].setValue(round(layer.position[0] * 100))
            self.position_y[1].setValue(round(layer.position[1] * 100))
            self.scale[1].setValue(round(layer.scale[0] * 100))
            self.rotation[1].setValue(round(layer.rotation))
            self._load_layer_effects(layer)
        for slider in sliders:
            slider.blockSignals(False)

    def _load_layer_effects(self, layer) -> None:
        values = normalize_layer_effects(layer.layer_effects)
        self.layer_fx_enabled.blockSignals(True)
        self.layer_fx_enabled.setChecked(values["enabled"])
        self.layer_fx_enabled.blockSignals(False)
        self._loading = True
        for key, (label, slider, title) in self.layer_fx_sliders.items():
            slider.blockSignals(True)
            scale = 1.0 if key == "hue" else 100.0
            value = round(float(values[key]) * scale)
            slider.setValue(value)
            slider.blockSignals(False)
            label.setText(f"{title}  {value}")
        self.layer_fx_preset.blockSignals(True)
        imported = self.application.composition.metadata.get("layer_fx_presets", {})
        known_names = list(LAYER_EFFECT_PRESETS) + (list(imported) if isinstance(imported, dict) else [])
        self.layer_fx_preset.clear()
        self.layer_fx_preset.addItems(list(dict.fromkeys(known_names)) + ["Custom"])
        self.layer_fx_preset.setCurrentText("Custom")
        for name in LAYER_EFFECT_PRESETS:
            if normalize_layer_effects({
                **LAYER_EFFECT_PRESETS[name],
                "enabled": name != "Clean",
            }) == values:
                self.layer_fx_preset.setCurrentText(name)
                break
        if isinstance(imported, dict):
            for name, stages in imported.items():
                if values["stages"] == normalize_layer_effects({"stages": stages})["stages"]:
                    self.layer_fx_preset.setCurrentText(str(name))
                    break
        self.layer_fx_preset.blockSignals(False)
        self.fx_stage_list.clear()
        for stage in values["stages"]:
            title = EFFECT_STAGE_TYPES[stage["type"]]
            item = QListWidgetItem(f'{title} · {stage["amount"]:.2f}')
            item.setData(Qt.ItemDataRole.UserRole, dict(stage))
            item.setCheckState(Qt.CheckState.Checked if stage["enabled"] else Qt.CheckState.Unchecked)
            self.fx_stage_list.addItem(item)
        self._loading = False

    def _commit_fx_stages(self) -> None:
        stages = []
        for index in range(self.fx_stage_list.count()):
            item = self.fx_stage_list.item(index)
            stage = dict(item.data(Qt.ItemDataRole.UserRole) or {})
            stage["enabled"] = item.checkState() == Qt.CheckState.Checked
            stages.append(stage)
        self._update_selected_layer_effects({"stages": stages})

    def _add_fx_stage(self) -> None:
        kind = self.fx_stage_type.currentData()
        item = QListWidgetItem(f'{EFFECT_STAGE_TYPES[kind]} · 1.00')
        item.setData(Qt.ItemDataRole.UserRole, {"type": kind, "amount": 1.0, "enabled": True})
        item.setCheckState(Qt.CheckState.Checked)
        self.fx_stage_list.addItem(item)
        self._commit_fx_stages()

    def _remove_fx_stage(self) -> None:
        row = self.fx_stage_list.currentRow()
        if row >= 0:
            self.fx_stage_list.takeItem(row)
            self._commit_fx_stages()

    def _move_fx_stage(self, offset: int) -> None:
        row = self.fx_stage_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.fx_stage_list.count():
            return
        item = self.fx_stage_list.takeItem(row)
        self.fx_stage_list.insertItem(target, item)
        self.fx_stage_list.setCurrentRow(target)
        self._commit_fx_stages()

    def _save_fx_chain(self) -> None:
        layer = self._selected_layer()
        if layer is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save layer FX chain", "layer-fx-chain.json", "JSON (*.json)")
        if not path:
            return
        import json
        payload = {"format": "eli_lab_layer_fx_chain", "version": 1,
                   "name": layer.name, "chain": normalize_layer_effects(layer.layer_effects)["stages"]}
        try:
            from pathlib import Path
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "FX chain", str(exc))

    def _export_fx_presets(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export project FX presets", "layer-fx-presets.json", "JSON (*.json)")
        if not path:
            return
        import json
        presets = {
            "Xerox Stack": [{"type": "monochrome", "amount": 1.0, "enabled": True}, {"type": "threshold", "amount": 0.45, "enabled": True}],
            "Negative Print": [{"type": "invert", "amount": 1.0, "enabled": True}, {"type": "posterize", "amount": 0.55, "enabled": True}],
            "Signal Scan": [{"type": "hue", "amount": 0.22, "enabled": True}, {"type": "scanlines", "amount": 0.7, "enabled": True}],
        }
        imported = self.application.composition.metadata.get("layer_fx_presets", {})
        if isinstance(imported, dict):
            presets.update(imported)
        try:
            from pathlib import Path
            Path(path).write_text(json.dumps({"format": "eli_lab_layer_fx_presets", "version": 1, "presets": presets}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "FX presets", str(exc))

    def _import_fx_presets(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import layer FX chain or presets", "", "JSON (*.json)")
        if not path:
            return
        import json
        from pathlib import Path
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if payload.get("format") == "eli_lab_layer_fx_chain":
                stages = normalize_layer_effects({"stages": payload.get("chain", [])})["stages"]
                self._update_selected_layer_effects({"stages": stages, "enabled": bool(stages)})
                self._load_layer_effects(self._selected_layer())
            elif payload.get("format") == "eli_lab_layer_fx_presets":
                presets = payload.get("presets", {})
                if not isinstance(presets, dict):
                    raise ValueError("Preset collection must be an object.")
                # Imported project presets are stored in composition metadata.
                safe = {str(name): normalize_layer_effects({"stages": stages})["stages"]
                        for name, stages in presets.items() if isinstance(stages, list)}
                self.application.composition.metadata["layer_fx_presets"] = safe
                QMessageBox.information(self, "FX presets", f"Imported {len(safe)} project preset(s).")
            else:
                raise ValueError("Unsupported FX preset file.")
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "FX presets", str(exc))

    def _update_selected_layer_effects(self, changes: dict[str, object]) -> None:
        layer = self._selected_layer()
        if layer is None or self._loading:
            return
        values = normalize_layer_effects(layer.layer_effects)
        values.update(changes)
        self.application.layer_manager.update_layer(
            layer.id,
            layer_effects=normalize_layer_effects(values),
            fx_manual_override_until=time.time() + 30.0,
        )

    def _layer_fx_enabled_changed(self, enabled: bool) -> None:
        self._update_selected_layer_effects({"enabled": bool(enabled)})

    def _layer_fx_preset_changed(self, name: str) -> None:
        if name == "Custom" or self._loading:
            return
        from effects.layer_settings import apply_layer_effect_preset

        layer = self._selected_layer()
        if layer is None:
            return
        imported = self.application.composition.metadata.get("layer_fx_presets", {})
        if isinstance(imported, dict) and name in imported:
            stages = normalize_layer_effects({"stages": imported[name]})["stages"]
            values = normalize_layer_effects({"enabled": bool(stages), "stages": stages})
        else:
            values = apply_layer_effect_preset(name)
        self.application.layer_manager.update_layer(
            layer.id,
            layer_effects=values,
            fx_manual_override_until=time.time() + 30.0,
        )
        self._loading = True
        self._load_layer_effects(layer)
        self._loading = False

    def _layer_fx_value_changed(self, key: str, value: int) -> None:
        if self._loading:
            return
        scale = 1.0 if key == "hue" else 100.0
        mapped = value / scale
        self._update_selected_layer_effects({key: mapped})
        self.layer_fx_preset.blockSignals(True)
        self.layer_fx_preset.setCurrentText("Custom")
        self.layer_fx_preset.blockSignals(False)

    def remove_selected_layer(self) -> None:
        layer = self._selected_layer()
        if layer is None:
            return
        self.application.remove_layer(layer.id)
        self.refresh()
        self.layers_changed.emit()

    def _visibility_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        layer_id = item.data(Qt.ItemDataRole.UserRole)
        if layer_id:
            self.application.layer_manager.update_layer(
                layer_id,
                visible=item.checkState() == Qt.CheckState.Checked,
            )

    def _opacity_changed(self, layer_id: str, value: int) -> None:
        self.application.layer_manager.update_layer(layer_id, opacity=value / 100.0)

    def _blend_changed(self, layer_id: str, value: str) -> None:
        self.application.layer_manager.update_layer(layer_id, blend_mode=value)

    def _position_x_changed(self, value: int) -> None:
        layer = self._selected_layer()
        if layer:
            self.application.layer_manager.update_layer(
                layer.id, position=(value / 100.0, layer.position[1])
            )

    def _position_y_changed(self, value: int) -> None:
        layer = self._selected_layer()
        if layer:
            self.application.layer_manager.update_layer(
                layer.id, position=(layer.position[0], value / 100.0)
            )

    def _scale_changed(self, value: int) -> None:
        layer = self._selected_layer()
        if layer:
            amount = value / 100.0
            self.application.layer_manager.update_layer(
                layer.id, scale=(amount, amount)
            )

    def _rotation_changed(self, value: int) -> None:
        layer = self._selected_layer()
        if layer:
            self.application.layer_manager.update_layer(layer.id, rotation=float(value))
