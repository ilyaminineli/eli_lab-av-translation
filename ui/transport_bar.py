from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class TransportBar(QWidget):
    random_set_requested = Signal()
    random_layout_requested = Signal()
    lock_all_requested = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.random_set_button = QPushButton("RANDOM SET")
        self.random_layout_button = QPushButton("RANDOMIZE LAYOUT")
        self.lock_all_button = QPushButton("LOCK ALL")
        self.lock_all_button.setCheckable(True)
        self.random_set_button.clicked.connect(self.random_set_requested)
        self.random_layout_button.clicked.connect(self.random_layout_requested)
        self.lock_all_button.toggled.connect(self.lock_all_requested)
        layout.addWidget(self.random_set_button)
        layout.addWidget(self.random_layout_button)
        layout.addStretch(1)
        layout.addWidget(self.lock_all_button)
