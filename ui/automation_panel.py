from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.automation import AutomationSettings
from media.library import MediaLibrary


class AutomationPanel(QWidget):
    start_requested = Signal(object, object, object)
    stop_requested = Signal()

    def __init__(self, library: MediaLibrary, parent=None) -> None:
        super().__init__(parent)
        self.library = library
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        form = QFormLayout()

        self.collection_combo = QComboBox()
        form.addRow("FOOTAGE POOL", self.collection_combo)

        self.duration_combo = QComboBox()
        for label, seconds in (
            ("30 minutes", 1800),
            ("45 minutes", 2700),
            ("1 hour", 3600),
            ("90 minutes", 5400),
            ("2 hours", 7200),
            ("Until stopped", None),
        ):
            self.duration_combo.addItem(label, seconds)
        form.addRow("SESSION LENGTH", self.duration_combo)

        self.cut_combo = QComboBox()
        self.cut_combo.addItem("Slow cuts · 18–38 sec", "slow")
        self.cut_combo.addItem("Balanced · 8–24 sec", "balanced")
        self.cut_combo.addItem("Fast cuts · 3–10 sec", "fast")
        self.cut_combo.setCurrentIndex(1)
        form.addRow("CUT RHYTHM", self.cut_combo)

        self.segment_combo = QComboBox()
        self.segment_combo.addItem("Short fragments · 2–6 sec", "short")
        self.segment_combo.addItem("Mixed fragments · 4–16 sec", "mixed")
        self.segment_combo.addItem("Long fragments · 12–30 sec", "long")
        self.segment_combo.setCurrentIndex(1)
        form.addRow("IN / OUT LENGTH", self.segment_combo)

        self.loop_combo = QComboBox()
        self.loop_combo.addItem("Occasional loops · 25%", 0.25)
        self.loop_combo.addItem("Mixed loops · 58%", 0.58)
        self.loop_combo.addItem("Frequent loops · 85%", 0.85)
        self.loop_combo.setCurrentIndex(1)
        form.addRow("SEGMENT LOOP CHANCE", self.loop_combo)

        layout.addLayout(form)
        self.layout_check = QCheckBox("Periodically change collage layout")
        self.layout_check.setChecked(True)
        self.effects_check = QCheckBox("Periodically change overlay / filter look")
        self.effects_check.setChecked(True)
        layout.addWidget(self.layout_check)
        layout.addWidget(self.effects_check)

        self.start_button = QPushButton("START AUTOMATIC SESSION")
        self.stop_button = QPushButton("STOP AUTOMATION")
        self.stop_button.setEnabled(False)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        self.status_label = QLabel("Ready · import a footage folder to begin.")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("mutedLabel")
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self.stop_requested)
        self.refresh_collections()

    def refresh_collections(self) -> None:
        selected = self.collection_combo.currentData()
        self.collection_combo.blockSignals(True)
        self.collection_combo.clear()
        self.collection_combo.addItem("All imported footage", None)
        groups: dict[str, list[str]] = {}
        for asset in self.library.list_assets():
            groups.setdefault(asset.collection_id, []).append(asset.path)
        for collection_id, paths in sorted(groups.items()):
            folder_name = Path(paths[0]).parent.name or "Video folder"
            self.collection_combo.addItem(
                f"{folder_name} · {len(paths)} clips",
                collection_id,
            )
        index = self.collection_combo.findData(selected)
        self.collection_combo.setCurrentIndex(index if index >= 0 else 0)
        self.collection_combo.blockSignals(False)

    def _build_settings(self) -> AutomationSettings:
        cut_ranges = {
            "slow": (18.0, 38.0),
            "balanced": (8.0, 24.0),
            "fast": (3.0, 10.0),
        }
        segment_ranges = {
            "short": (2.0, 6.0),
            "mixed": (4.0, 16.0),
            "long": (12.0, 30.0),
        }
        cut_min, cut_max = cut_ranges[self.cut_combo.currentData()]
        segment_min, segment_max = segment_ranges[self.segment_combo.currentData()]
        return AutomationSettings(
            min_segment_seconds=segment_min,
            max_segment_seconds=segment_max,
            min_cut_interval=cut_min,
            max_cut_interval=cut_max,
            loop_probability=float(self.loop_combo.currentData()),
            clip_switch_probability=0.42,
            randomize_layout=self.layout_check.isChecked(),
            randomize_effects=self.effects_check.isChecked(),
            min_layout_interval=max(8.0, cut_min * 1.25),
            max_layout_interval=max(16.0, cut_max * 1.8),
            min_effect_interval=max(7.0, cut_min * 1.1),
            max_effect_interval=max(14.0, cut_max * 1.5),
        )

    def _start(self) -> None:
        self.start_requested.emit(
            self.collection_combo.currentData(),
            self.duration_combo.currentData(),
            self._build_settings(),
        )

    def set_running(self, running: bool, message: str | None = None) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        if message:
            self.status_label.setText(message)

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)
