from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from core.application import Application
from ui.deck_panel import DeckPanel
from ui.layer_panel import LayerPanel
from ui.media_browser import MediaBrowser
from ui.performance_view import PerformanceView
from ui.transport_bar import TransportBar

_LOG = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, application: Application) -> None:
        super().__init__()
        self.application = application
        self.setWindowTitle("ELI LAB AV Translation")
        self.resize(1500, 920)
        self.setMinimumSize(1050, 680)

        self.performance_view = PerformanceView(application, self)
        self.setCentralWidget(self.performance_view)

        self.media_browser = MediaBrowser(application.media_library, self)
        self.media_dock = self._make_dock("MEDIA LIBRARY", self.media_browser)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.media_dock)

        self.deck_panel = DeckPanel(application, self)
        self.deck_dock = self._make_dock("VIDEO DECKS", self.deck_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.deck_dock)

        self.layer_panel = LayerPanel(application, self)
        self.layer_dock = self._make_dock("LAYERS", self.layer_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layer_dock)

        self.transport_bar = TransportBar(self)
        toolbar = QToolBar("Performance")
        toolbar.setMovable(False)
        toolbar.addWidget(self.transport_bar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.status_label = QLabel("Initializing OpenGL…")
        self.statusBar().addPermanentWidget(self.status_label)
        self.performance_view.render_status_changed.connect(self.status_label.setText)

        self.media_browser.assign_requested.connect(self.assign_media)
        self.deck_panel.action_requested.connect(self.deck_action)
        self.deck_panel.loop_changed.connect(self.set_deck_loop)
        self.transport_bar.random_set_requested.connect(self.randomize_decks)
        self.transport_bar.random_layout_requested.connect(self.randomize_layout)
        self.transport_bar.lock_all_requested.connect(self.lock_all)

        self._create_actions()
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AllowNestedDocks
        )

    def _make_dock(self, title: str, widget) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(title.lower().replace(" ", "_"))
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        return dock

    def _create_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save Project &As…", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        import_action = QAction("Add Media &Folder…", self)
        import_action.triggered.connect(self.media_browser.choose_folder)
        file_menu.addAction(import_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.media_dock.toggleViewAction())
        view_menu.addAction(self.deck_dock.toggleViewAction())
        view_menu.addAction(self.layer_dock.toggleViewAction())

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def assign_media(self, asset: object, deck_id: str) -> None:
        try:
            self.application.assign_media_to_deck(asset, deck_id)
            self.deck_panel.refresh()
            self.statusBar().showMessage(
                f"Loaded {getattr(asset, 'name', 'video')} into {deck_id.upper()}",
                4000,
            )
        except Exception as exc:
            _LOG.exception("Could not assign media to deck")
            QMessageBox.critical(self, "Video load failed", str(exc))

    def deck_action(self, deck_id: str, action: str) -> None:
        deck = self.application.decks[deck_id]
        try:
            if action == "play":
                deck.play()
            elif action == "pause":
                deck.pause()
            elif action == "stop":
                deck.stop()
            self.deck_panel.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Deck error", str(exc))

    def set_deck_loop(self, deck_id: str, enabled: bool) -> None:
        self.application.decks[deck_id].set_loop(enabled)

    def randomize_decks(self) -> None:
        assets = self.application.media_library.list_assets()
        count = self.application.performance_manager.randomize_decks(
            assets,
            self.application.decks.values(),
        )
        self.deck_panel.refresh()
        self.statusBar().showMessage(f"Assigned {count} video deck(s).", 3000)

    def randomize_layout(self) -> None:
        count = self.application.performance_manager.randomize_layout(
            self.application.composition.layers
        )
        self.layer_panel.refresh()
        self.statusBar().showMessage(f"Randomized {count} layer(s).", 3000)

    def lock_all(self, locked: bool) -> None:
        for deck in self.application.decks.values():
            deck.locked = locked
        for layer in self.application.composition.layers:
            layer.locked = locked
        self.deck_panel.refresh()
        self.layer_panel.refresh()

    def new_project(self) -> None:
        answer = QMessageBox.question(
            self,
            "New project",
            "Create a new composition? Unsaved project changes will be lost.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.application.reset_project()
        self.deck_panel.refresh()
        self.layer_panel.refresh()
        self.statusBar().showMessage("New composition created.", 3000)

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open AV Translation project",
            "",
            "ELI AV Project (*.eliav);;JSON files (*.json)",
        )
        if not path:
            return
        try:
            self.application.load_project(path)
            self.deck_panel.refresh()
            self.layer_panel.refresh()
            self.statusBar().showMessage(f"Opened {Path(path).name}", 4000)
        except Exception as exc:
            _LOG.exception("Could not open project %s", path)
            QMessageBox.critical(self, "Project open failed", str(exc))

    def save_project(self) -> None:
        if self.application.current_project_path is None:
            self.save_project_as()
            return
        try:
            path = self.application.save_project(self.application.current_project_path)
            self.statusBar().showMessage(f"Saved {path.name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Project save failed", str(exc))

    def save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save AV Translation project",
            "Untitled.eliav",
            "ELI AV Project (*.eliav)",
        )
        if not path:
            return
        if not path.lower().endswith(".eliav"):
            path += ".eliav"
        try:
            saved = self.application.save_project(path)
            self.statusBar().showMessage(f"Saved {saved.name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Project save failed", str(exc))

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "About ELI LAB AV Translation",
            "ELI LAB AV Translation 0.1.0\n"
            "A modular live audiovisual compositor.\n\n"
            "M0: rendering core · M1: video collage",
        )

    def closeEvent(self, event) -> None:
        self.performance_view.shutdown_renderer()
        self.application.shutdown()
        super().closeEvent(event)
