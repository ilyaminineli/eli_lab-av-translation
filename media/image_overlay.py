from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage, QImageReader

from media.frame_queue import VideoFrameData


class ImageOverlayPlayer:
    """Read a still or Qt-supported animated image and publish RGBA frames."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        self.reader = QImageReader(str(self.path))
        self.reader.setAutoTransform(True)
        self.animated = bool(self.reader.supportsAnimation())
        image = self.reader.read()
        if image.isNull():
            raise ValueError(
                f"Could not decode overlay image {self.path}: {self.reader.errorString()}"
            )
        self._frame = self._convert(image)
        self._next_frame_at = time.perf_counter() + self._delay_seconds()
        self._revision = 1
        self._loop_count = self.reader.loopCount()
        self._completed_loops = 0

    @staticmethod
    def _convert(image: QImage) -> np.ndarray:
        rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
        width = rgba.width()
        height = rgba.height()
        stride = rgba.bytesPerLine()
        raw = rgba.bits().tobytes()
        rows = np.frombuffer(raw, dtype=np.uint8).reshape(height, stride)
        return rows[:, :width * 4].reshape(height, width, 4).copy()

    def _delay_seconds(self) -> float:
        delay_ms = int(self.reader.nextImageDelay())
        if delay_ms <= 0:
            return 0.1
        return max(0.02, min(10.0, delay_ms / 1000.0))

    @property
    def frame(self) -> VideoFrameData:
        height, width, _ = self._frame.shape
        return VideoFrameData(
            pixels=self._frame,
            width=width,
            height=height,
            timestamp=time.perf_counter(),
        )

    @property
    def revision(self) -> int:
        return self._revision

    def update(self, now: float | None = None) -> VideoFrameData | None:
        if not self.animated:
            return None
        current = time.perf_counter() if now is None else float(now)
        if current < self._next_frame_at:
            return None
        image = self.reader.read()
        if image.isNull():
            self._completed_loops += 1
            if self._loop_count >= 0 and self._completed_loops >= self._loop_count:
                return None
            if not self.reader.jumpToImage(0):
                return None
            image = self.reader.read()
            if image.isNull():
                return None
        self._frame = self._convert(image)
        self._revision += 1
        self._next_frame_at = current + self._delay_seconds()
        return self.frame


    def close(self) -> None:
        self.reader = QImageReader()
        self._frame = np.zeros((1, 1, 4), dtype=np.uint8)
