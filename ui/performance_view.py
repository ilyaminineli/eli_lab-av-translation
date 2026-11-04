from __future__ import annotations

import logging
import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from core.application import Application
from core.render_engine import RenderEngine

_LOG = logging.getLogger(__name__)


class PerformanceView(QOpenGLWidget):
    """Qt OpenGL output surface used for preview and external projector windows."""

    render_status_changed = Signal(str)

    def __init__(self, application: Application, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        self.engine = RenderEngine()
        self._initialization_error: str | None = None
        self._last_fps_time = time.perf_counter()
        self._frame_count = 0
        self.setMinimumSize(640, 360)
        self.setObjectName("masterPerformanceView")

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def initializeGL(self) -> None:
        try:
            self.engine.initialize()
            self._initialization_error = None
            self.render_status_changed.emit(
                f"OpenGL ready · {self.engine.renderer_name}"
            )
        except Exception as exc:
            self._initialization_error = str(exc)
            _LOG.exception("Could not initialize the OpenGL renderer")

    def paintGL(self) -> None:
        if self._initialization_error:
            self._paint_message(
                "RENDERER INITIALIZATION FAILED",
                self._initialization_error,
            )
            return
        if not self.engine.initialized:
            self._paint_message("INITIALIZING RENDERER", "Waiting for OpenGL context…")
            return

        ratio = self.devicePixelRatioF()
        width = max(1, round(self.width() * ratio))
        height = max(1, round(self.height() * ratio))
        try:
            self.engine.render(
                self.application.composition,
                self.application.current_frames(),
                int(self.defaultFramebufferObject()),
                width,
                height,
                effects=self.application.effects,
            )
        except Exception as exc:
            self._initialization_error = str(exc)
            _LOG.exception("Render frame failed")
            return

        self._frame_count += 1
        elapsed = time.perf_counter() - self._last_fps_time
        if elapsed >= 1.0:
            fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_fps_time = time.perf_counter()
            self.render_status_changed.emit(
                f"{fps:0.1f} FPS · {self.engine.renderer_name}"
            )

    def _paint_message(self, title: str, detail: str) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101114"))
        painter.setPen(QColor("#E5E5E8"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        painter.setFont(title_font)
        painter.drawText(
            self.rect().adjusted(28, 28, -28, -28),
            0x0001 | 0x0080,
            title,
        )
        painter.setPen(QColor("#A7A9B0"))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(
            self.rect().adjusted(28, 72, -28, -28),
            0x0001 | 0x0080,
            detail,
        )
        painter.end()

    def shutdown_renderer(self) -> None:
        self._timer.stop()
        if self.engine.initialized and self.isValid():
            self.makeCurrent()
            try:
                self.engine.release()
            finally:
                self.doneCurrent()
