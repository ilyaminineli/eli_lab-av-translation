from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.application import Application

_BLEND_MODES = ("normal", "add", "screen", "multiply", "difference")


class LayerPanel(QWidget):
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

        transform_group = QGroupBox("SELECTED LAYER TRANSFORM")
        transform_layout = QVBoxLayout(transform_group)
        self.position_x = self._add_slider(transform_layout, "X POSITION", 0, 100, 50)
        self.position_y = self._add_slider(transform_layout, "Y POSITION", 0, 100, 50)
        self.scale = self._add_slider(transform_layout, "UNIFORM SCALE", 10, 200, 100)
        self.rotation = self._add_slider(transform_layout, "ROTATION", -180, 180, 0)
        layout.addWidget(transform_group)

        self.position_x[1].valueChanged.connect(self._position_x_changed)
        self.position_y[1].valueChanged.connect(self._position_y_changed)
        self.scale[1].valueChanged.connect(self._scale_changed)
        self.rotation[1].valueChanged.connect(self._rotation_changed)
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

    def refresh(self) -> None:
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
            self.table.setCurrentCell(0, 1)
            self._selection_changed(0, 1, -1, -1)

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
        if layer is None:
            self.position_x[1].setEnabled(False)
            self.position_y[1].setEnabled(False)
            self.scale[1].setEnabled(False)
            self.rotation[1].setEnabled(False)
        else:
            self.position_x[1].setEnabled(True)
            self.position_y[1].setEnabled(True)
            self.scale[1].setEnabled(True)
            self.rotation[1].setEnabled(True)
            self.position_x[1].setValue(round(layer.position[0] * 100))
            self.position_y[1].setValue(round(layer.position[1] * 100))
            self.scale[1].setValue(round(layer.scale[0] * 100))
            self.rotation[1].setValue(round(layer.rotation))
        for slider in sliders:
            slider.blockSignals(False)

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
