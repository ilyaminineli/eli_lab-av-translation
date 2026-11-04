from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, QThreadPool, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from media.library import MediaLibrary
from media.models import MediaAsset
from media.thumbnails import generate_thumbnail

_LOG = logging.getLogger(__name__)


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    thumbnail_ready = Signal(str, str)


class ScanWorker(QRunnable):
    def __init__(self, library: MediaLibrary, folder: str) -> None:
        super().__init__()
        self.library = library
        self.folder = folder
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.result.emit(self.library.add_folder(self.folder))
        except Exception as exc:
            self.signals.error.emit(str(exc))


class ThumbnailWorker(QRunnable):
    def __init__(self, asset: MediaAsset) -> None:
        super().__init__()
        self.asset = asset
        self.signals = WorkerSignals()

    def run(self) -> None:
        result = generate_thumbnail(self.asset.path, self.asset.id)
        if result:
            self.signals.thumbnail_ready.emit(self.asset.id, str(result))


class MediaBrowser(QWidget):
    assign_requested = Signal(object, str)
    library_updated = Signal()

    def __init__(self, library: MediaLibrary, parent=None) -> None:
        super().__init__(parent)
        self.library = library
        self.thread_pool = QThreadPool.globalInstance()
        self._assets: dict[str, MediaAsset] = {}
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.add_folder_button = QPushButton("ADD FOLDER")
        self.add_folder_button.clicked.connect(self.choose_folder)
        top.addWidget(self.add_folder_button)
        layout.addLayout(top)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Assign to"))
        self.deck_combo = QComboBox()
        for deck_id, label in (
            ("deck_a", "Deck A"),
            ("deck_b", "Deck B"),
            ("deck_c", "Deck C"),
            ("deck_d", "Deck D"),
        ):
            self.deck_combo.addItem(label, deck_id)
        target_row.addWidget(self.deck_combo, 1)
        layout.addLayout(target_row)

        self.asset_list = QListWidget()
        self.asset_list.setIconSize(QSize(112, 64))
        self.asset_list.itemDoubleClicked.connect(self.assign_item)
        layout.addWidget(self.asset_list, 1)

        self.status_label = QLabel("Add a folder containing video footage.")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("mutedLabel")
        layout.addWidget(self.status_label)

        self.refresh()

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add video folder")
        if folder:
            self.scan_folder(folder)

    def scan_folder(self, folder: str) -> None:
        self.add_folder_button.setEnabled(False)
        self.status_label.setText(f"Scanning {folder}…")
        worker = ScanWorker(self.library, folder)
        worker.signals.result.connect(self.scan_finished)
        worker.signals.error.connect(self.scan_failed)
        self.thread_pool.start(worker)

    def dragEnterEvent(self, event) -> None:
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        folders = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_dir()
        ]
        if not folders:
            event.ignore()
            return
        for folder in folders:
            self.scan_folder(folder)
        event.acceptProposedAction()

    def scan_finished(self, assets: list[MediaAsset]) -> None:
        self.add_folder_button.setEnabled(True)
        self.refresh()
        self.status_label.setText(f"Indexed {len(assets)} video file(s).")
        self.library_updated.emit()
        for asset in assets:
            if not asset.thumbnail_path:
                worker = ThumbnailWorker(asset)
                worker.signals.thumbnail_ready.connect(self.thumbnail_ready)
                self.thread_pool.start(worker)

    def scan_failed(self, message: str) -> None:
        self.add_folder_button.setEnabled(True)
        self.status_label.setText(f"Scan failed: {message}")
        _LOG.error("Media scan failed: %s", message)

    def thumbnail_ready(self, asset_id: str, thumbnail_path: str) -> None:
        self.library.update_thumbnail(asset_id, thumbnail_path)
        for index in range(self.asset_list.count()):
            item = self.asset_list.item(index)
            asset = item.data(Qt.ItemDataRole.UserRole)
            if asset and asset.id == asset_id:
                item.setIcon(QIcon(thumbnail_path))
                break

    def refresh(self) -> None:
        self.asset_list.clear()
        self._assets.clear()
        assets = self.library.list_assets()
        for asset in assets:
            self._assets[asset.id] = asset
            item = QListWidgetItem(asset.name)
            item.setData(Qt.ItemDataRole.UserRole, asset)
            if asset.thumbnail_path and Path(asset.thumbnail_path).is_file():
                item.setIcon(QIcon(asset.thumbnail_path))
            item.setToolTip(asset.path)
            self.asset_list.addItem(item)
        if assets:
            self.status_label.setText(f"{len(assets)} asset(s) in library.")
        else:
            self.status_label.setText("Add a folder containing video footage.")

    def assign_item(self, item: QListWidgetItem) -> None:
        asset = item.data(Qt.ItemDataRole.UserRole)
        if asset is not None:
            self.assign_requested.emit(asset, str(self.deck_combo.currentData()))
