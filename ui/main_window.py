from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from config import APP_VERSION
from core.application import Application
from ui.automation_panel import AutomationPanel
from ui.deck_panel import DeckPanel
from ui.effects_panel import EffectsPanel
from ui.generators_panel import GeneratorsPanel
from ui.layer_panel import LayerPanel
from ui.media_browser import MediaBrowser
from ui.output_window import OutputWindowManager
from ui.performance_view import PerformanceView
from ui.transport_bar import TransportBar

_LOG = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, application: Application) -> None:
        super().__init__()
        self.application = application
        self.output_manager = OutputWindowManager(application, self)
        self.setWindowTitle(f"eli_lab AV Translation {APP_VERSION}")
        self.resize(1600, 980)
        self.setMinimumSize(1100, 700)

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

        self.effects_panel = EffectsPanel(application.effects, self)
        self.effects_dock = self._make_dock("EFFECTS + OVERLAYS", self.effects_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.effects_dock)
        self.tabifyDockWidget(self.layer_dock, self.effects_dock)

        self.generators_panel = GeneratorsPanel(application, self)
        self.generators_dock = self._make_dock("GENERATORS + TEXT ART", self.generators_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.generators_dock)
        self.tabifyDockWidget(self.effects_dock, self.generators_dock)

        self.automation_panel = AutomationPanel(application.media_library, self)
        self.automation_dock = self._make_dock("AUTO PERFORMANCE", self.automation_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.automation_dock)
        self.tabifyDockWidget(self.generators_dock, self.automation_dock)
        self.layer_dock.raise_()

        self.transport_bar = TransportBar(self)
        toolbar = QToolBar("Performance")
        toolbar.setMovable(False)
        toolbar.addWidget(self.transport_bar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.status_label = QLabel("Initializing OpenGL…")
        self.statusBar().addPermanentWidget(self.status_label)
        self.performance_view.render_status_changed.connect(self.status_label.setText)

        self.media_browser.assign_requested.connect(self.assign_media)
        self.media_browser.library_updated.connect(self.automation_panel.refresh_collections)
        self.media_browser.library_updated.connect(self.refresh_automation_media_pool)
        self.deck_panel.action_requested.connect(self.deck_action)
        self.deck_panel.loop_changed.connect(self.set_deck_loop)
        self.transport_bar.random_set_requested.connect(self.randomize_decks)
        self.transport_bar.random_layout_requested.connect(self.randomize_layout)
        self.transport_bar.lock_all_requested.connect(self.lock_all)
        self.automation_panel.start_requested.connect(self.start_automation)
        self.automation_panel.stop_requested.connect(self.stop_automation)
        self.generators_panel.composition_changed.connect(self.layer_panel.refresh)

        self._create_actions()
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AllowNestedDocks
        )

        self._runtime_timer = QTimer(self)
        # Refresh queues and automation at the configured render cadence.
        self._runtime_timer.setInterval(33)
        self._runtime_timer.timeout.connect(self._runtime_tick)
        self._runtime_timer.start()

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(500)
        self._status_timer.timeout.connect(self._refresh_automation_status)
        self._status_timer.start()

    def _make_dock(self, title: str, widget) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(title.lower().replace(" ", "_").replace("+", "plus").replace(" ", "_"))
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
        for dock in (
                self.media_dock,
                self.deck_dock,
                self.layer_dock,
                self.effects_dock,
                self.generators_dock,
                self.automation_dock,
        ):
            view_menu.addAction(dock.toggleViewAction())

        output_menu = view_menu.addMenu("PROJECTOR OUTPUT")
        output_menu.aboutToShow.connect(
            lambda menu=output_menu: self._populate_projector_menu(menu)
        )
        QGuiApplication.screenAdded.connect(self._display_configuration_changed)
        QGuiApplication.screenRemoved.connect(self._display_configuration_changed)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _populate_projector_menu(self, menu) -> None:
        menu.clear()
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        if not screens:
            unavailable = QAction("No displays detected", menu)
            unavailable.setEnabled(False)
            menu.addAction(unavailable)
        for index, screen in enumerate(screens, start=1):
            geometry = screen.geometry()
            primary_label = " · PRIMARY" if screen == primary else ""
            label = (
                f"Display {index} · {screen.name()} "
                f"({geometry.width()}×{geometry.height()}){primary_label}"
            )
            action = QAction(label, menu)
            action.triggered.connect(
                lambda checked=False, target=screen: self.open_projector_output(target)
            )
            menu.addAction(action)
        menu.addSeparator()
        close_output_action = QAction("Close Projector Output", menu)
        close_output_action.setEnabled(self.output_manager.window is not None)
        close_output_action.triggered.connect(self.output_manager.close)
        menu.addAction(close_output_action)

    def _display_configuration_changed(self, *_args) -> None:
        self.statusBar().showMessage(
            f"Display configuration changed · {len(QGuiApplication.screens())} display(s) detected",
            5000,
        )

    def open_projector_output(self, screen) -> None:
        try:
            self.output_manager.open_on_screen(screen)
            self.statusBar().showMessage(
                (
                    f"Projector output opened on {screen.name()}. "
                    "Press Escape on the output to close it."
                ),
                6000,
            )
        except Exception as exc:
            _LOG.exception("Could not open projector output")
            QMessageBox.critical(self, "Projector output failed", str(exc))

    def refresh_automation_media_pool(self) -> None:
        if self.application.refresh_automation_media_pool():
            self._refresh_automation_status()

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

    def start_automation(
            self,
            collection_id: str | None,
            duration_seconds: float | None,
            settings,
    ) -> None:
        try:
            count = self.application.start_automation(
                collection_id=collection_id,
                settings=settings,
                duration_seconds=duration_seconds,
            )
            self.deck_panel.refresh()
            self.layer_panel.refresh()
            self.effects_panel.sync_from_settings()
            self.automation_panel.set_running(
                True,
                f"Running · {count} deck(s) automated. Layouts and looks will change on their own.",
            )
            self._refresh_automation_status()
        except Exception as exc:
            _LOG.exception("Could not start automation")
            self.automation_panel.set_running(False, f"Could not start · {exc}")
            QMessageBox.warning(self, "Automation could not start", str(exc))

    def stop_automation(self) -> None:
        self.application.stop_automation()
        self.automation_panel.set_running(
            False,
            "Stopped · video decks keep their current playback.",
        )

    def _runtime_tick(self) -> None:
        self.application.refresh_frames()
        was_running = self.application.automation.running
        changed = self.application.tick_automation()
        if changed:
            self.deck_panel.refresh()
            self.layer_panel.refresh()
            self.effects_panel.sync_from_settings()
        if was_running and not self.application.automation.running:
            self.automation_panel.set_running(
                False,
                self.application.automation.last_action,
            )

    def _refresh_automation_status(self) -> None:
        director = self.application.automation
        if not director.running:
            return
        remaining = director.remaining_seconds()
        if remaining is None:
            time_label = "until stopped"
        else:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            time_label = f"{minutes:02d}:{seconds:02d} remaining"
        self.automation_panel.set_status(f"RUNNING · {director.last_action} · {time_label}")

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
        self.effects_panel.sync_from_settings()
        self.generators_panel.refresh()
        self.automation_panel.set_running(False, "Ready · import footage to begin.")
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
            self.effects_panel.sync_from_settings()
            self.generators_panel.refresh()
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
            "About eli_lab AV Translation",
            f"eli_lab AV Translation {APP_VERSION}\n"
            "Video collage, generative visuals, text art and projector output.\n\n"
            "Audio and Sonic Pi features remain separate future milestones.",
        )

    def closeEvent(self, event) -> None:
        self._runtime_timer.stop()
        self._status_timer.stop()
        self.media_browser.shutdown_workers()
        self.output_manager.close()
        self.performance_view.shutdown_renderer()
        self.application.shutdown()
        super().closeEvent(event)
