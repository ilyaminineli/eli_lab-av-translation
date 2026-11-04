from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
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
        layout.addWidget(self.table)
        self.refresh()

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
