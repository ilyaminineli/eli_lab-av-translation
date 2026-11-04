from __future__ import annotations

import logging
import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from config import RENDER_TARGET_FPS
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
        self._render_time_sum_ms = 0.0
        self._upload_time_sum_ms = 0.0
        self.setMinimumSize(640, 360)
        self.setObjectName("masterPerformanceView")

        self._timer = QTimer(self)
        interval_ms = max(1, round(1000.0 / max(1, RENDER_TARGET_FPS)))
        self._timer.setInterval(interval_ms)
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
        self._render_time_sum_ms += self.engine.last_render_ms
        self._upload_time_sum_ms += self.engine.last_upload_ms
        elapsed = time.perf_counter() - self._last_fps_time
        if elapsed >= 1.0:
            fps = self._frame_count / elapsed
            average_render_ms = self._render_time_sum_ms / max(1, self._frame_count)
            average_upload_ms = self._upload_time_sum_ms / max(1, self._frame_count)
            stats = self.application.performance_snapshot()
            self._frame_count = 0
            self._render_time_sum_ms = 0.0
            self._upload_time_sum_ms = 0.0
            self._last_fps_time = time.perf_counter()
            decode_ms_per_frame = (
                float(stats["decode_time_ms"]) / max(1, int(stats["decoded_frames"]))
            )
            convert_ms_per_frame = (
                float(stats["conversion_time_ms"]) / max(1, int(stats["published_frames"]))
            )
            status = (
                f"{fps:0.1f} FPS · decode {decode_ms_per_frame:0.1f} "
                f"ms/f · convert {convert_ms_per_frame:0.1f} ms/f · "
                f"render CPU {average_render_ms:0.1f} ms "
                f"(upload {average_upload_ms:0.1f} ms) · "
                f"{stats['playing_decks']} decks · "
                f"drop {stats['dropped_frames']} · "
                f"{self.engine.renderer_name}"
            )
            self.render_status_changed.emit(status)

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
