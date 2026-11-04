from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from config import APP_VERSION
from core.application import Application
from ui.asset_library_panel import AssetLibraryPanel
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
        self.setMinimumSize(980, 640)
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AllowNestedDocks
        )
        self._ui_settings = QSettings()
        self._restore_local_preview_on_close = False

        self.performance_view = PerformanceView(application, self)

        self.media_browser = MediaBrowser(application.media_library, self)
        self.media_dock = self._make_dock("MEDIA LIBRARY", self.media_browser)
        self.media_dock.setMinimumWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.media_dock)

        self.asset_library_panel = AssetLibraryPanel(application, self)
        self.asset_library_dock = self._make_dock("VISUAL ASSET LIBRARY", self.asset_library_panel)
        self.asset_library_dock.setMinimumWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.asset_library_dock)
        self.tabifyDockWidget(self.media_dock, self.asset_library_dock)

        self.deck_panel = DeckPanel(application, self)
        self.deck_dock = self._make_dock("VIDEO DECKS", self.deck_panel)
        self.deck_dock.setMinimumHeight(150)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.deck_dock)

        self.layer_panel = LayerPanel(application, self)
        self.layer_dock = self._make_dock("LAYERS", self.layer_panel)
        self.layer_dock.setMinimumWidth(300)
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

        # Local preview is a normal dock, not the central widget. It can be
        # resized, floated, tabified or hidden without taking space from controls.
        self.preview_dock = self._make_dock("LOCAL PREVIEW", self.performance_view)
        self.preview_dock.setMinimumSize(260, 180)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.preview_dock)
        self.tabifyDockWidget(self.automation_dock, self.preview_dock)
        self.layer_dock.raise_()
        self.setCentralWidget(self._build_workspace())

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
        self.layer_panel.layers_changed.connect(self.generators_panel.refresh)
        self.asset_library_panel.composition_changed.connect(self.layer_panel.refresh)
        self.asset_library_panel.composition_changed.connect(self.generators_panel.refresh)

        self._create_actions()
        saved_geometry = self._ui_settings.value("ui/main_window_geometry")
        saved_state = self._ui_settings.value("ui/main_window_state_v2")
        restored = False
        if saved_geometry and saved_state:
            restored = (
                self.restoreGeometry(saved_geometry)
                and self.restoreState(saved_state, 2)
            )
        if not restored:
            QTimer.singleShot(0, self._apply_default_dock_sizes)

        self._runtime_timer = QTimer(self)
        # Refresh queues and automation at the configured render cadence.
        self._runtime_timer.setInterval(33)
        self._runtime_timer.timeout.connect(self._runtime_tick)
        self._runtime_timer.start()

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(500)
        self._status_timer.timeout.connect(self._refresh_automation_status)
        self._status_timer.start()

    def _build_workspace(self) -> QWidget:
        workspace = QWidget(self)
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(14)
        layout.addStretch(1)

        eyebrow = QLabel("ELI LAB  /  AV TRANSLATION")
        eyebrow.setObjectName("mutedLabel")
        layout.addWidget(eyebrow, alignment=Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("PERFORMANCE WORKSPACE")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        description = QLabel(
            "The live canvas now lives in a dockable local preview. "
            "Keep the workspace for media, layers, effects and performance controls, "
            "or open the projector on a separate display."
        )
        description.setWordWrap(True)
        description.setMaximumWidth(620)
        description.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(description, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.workspace_output_label = QLabel("OUTPUT  ·  LOCAL PREVIEW")
        self.workspace_output_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.workspace_output_label.setObjectName("mutedLabel")
        layout.addWidget(self.workspace_output_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.show_preview_button = QPushButton("OPEN LOCAL PREVIEW")
        self.show_preview_button.clicked.connect(self.show_local_preview)
        actions.addWidget(self.show_preview_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(2)
        return workspace

    def _apply_default_dock_sizes(self) -> None:
        self.resizeDocks(
            [self.media_dock],
            [330],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks(
            [self.layer_dock],
            [350],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks(
            [self.deck_dock],
            [185],
            Qt.Orientation.Vertical,
        )

    def show_local_preview(self) -> None:
        self.preview_dock.show()
        self.preview_dock.raise_()

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

        overlay_action = QAction("Add Image / Video Overlay…", self)
        overlay_action.triggered.connect(self.add_overlay_media)
        file_menu.addAction(overlay_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("&View")
        for dock in (
                self.media_dock,
                self.asset_library_dock,
                self.deck_dock,
                self.layer_dock,
                self.effects_dock,
                self.generators_dock,
                self.automation_dock,
                self.preview_dock,
        ):
            view_menu.addAction(dock.toggleViewAction())

        output_menu = view_menu.addMenu("PROJECTOR OUTPUT")
        output_menu.aboutToShow.connect(
            lambda menu=output_menu: self._populate_projector_menu(menu)
        )
        gui_application = QGuiApplication.instance()
        if gui_application is not None:
            gui_application.screenAdded.connect(self._display_configuration_changed)
            gui_application.screenRemoved.connect(self._display_configuration_changed)

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
            if self.output_manager.window is not None:
                self.output_manager.close()
            self._restore_local_preview_on_close = self.preview_dock.isVisible()
            window = self.output_manager.open_on_screen(screen)
            window.closed.connect(self._projector_output_closed)
            if self._restore_local_preview_on_close:
                self.preview_dock.hide()
            self.workspace_output_label.setText(
                f"OUTPUT  ·  PROJECTOR  ·  {screen.name()}"
            )
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

    def _projector_output_closed(self) -> None:
        self.workspace_output_label.setText("OUTPUT  ·  LOCAL WORKSPACE")
        if self._restore_local_preview_on_close:
            self.preview_dock.show()
            self.preview_dock.raise_()
        self._restore_local_preview_on_close = False

    def refresh_automation_media_pool(self) -> None:
        if self.application.refresh_automation_media_pool():
            self._refresh_automation_status()

    def add_overlay_media(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Add image or video overlay",
            "",
            (
                "Overlay media (*.png *.apng *.gif *.webp *.jpg *.jpeg *.bmp "
                "*.mp4 *.mov *.mkv *.avi *.webm *.m4v)"
            ),
        )
        if not path:
            return
        try:
            layer = self.application.add_media_overlay(path)
            self.layer_panel.refresh()
            self.generators_panel.refresh()
            self.statusBar().showMessage(f"Added overlay {layer.name}", 4000)
        except Exception as exc:
            _LOG.exception("Could not add overlay media")
            QMessageBox.warning(self, "Overlay load failed", str(exc))

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
                (
                    f"Running · {count} deck(s) automated. Layouts, generator text "
                    "and layer FX will evolve automatically."
                ),
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
            self.generators_panel.refresh()
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
        self._ui_settings.setValue("ui/main_window_geometry", self.saveGeometry())
        self._ui_settings.setValue("ui/main_window_state_v2", self.saveState(2))
        self._runtime_timer.stop()
        self._status_timer.stop()
        self.media_browser.shutdown_workers()
        self.output_manager.close()
        self.performance_view.shutdown_renderer()
        self.application.shutdown()
        super().closeEvent(event)
