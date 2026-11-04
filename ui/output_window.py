from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from core.application import Application
from ui.performance_view import PerformanceView


class OutputWindow(QMainWindow):
    closed = Signal()

    def __init__(self, application: Application, screen, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("eli_lab AV Translation · Projector Output")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setCentralWidget(PerformanceView(application, self))
        self.performance_view: PerformanceView = self.centralWidget()
        self.setGeometry(screen.geometry())
        self._escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self._escape_shortcut.activated.connect(self.close)

    def closeEvent(self, event) -> None:
        self.performance_view.shutdown_renderer()
        self.closed.emit()
        super().closeEvent(event)


class OutputWindowManager:
    """Manages one independent fullscreen output on a selected Qt display."""

    def __init__(self, application: Application, parent=None) -> None:
        self.application = application
        self.parent = parent
        self.window: OutputWindow | None = None

    def open_on_screen(self, screen) -> OutputWindow:
        self.close()
        window = OutputWindow(self.application, screen, self.parent)
        window.closed.connect(self._forget_window)
        self.window = window
        window.winId()
        handle = window.windowHandle()
        if handle is not None:
            handle.setScreen(screen)
        window.showFullScreen()
        window.raise_()
        return window

    def close(self) -> None:
        if self.window is not None:
            window = self.window
            self.window = None
            window.close()

    def _forget_window(self) -> None:
        self.window = None
