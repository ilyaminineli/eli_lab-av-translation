from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class VideoFrameData:
    pixels: np.ndarray
    width: int
    height: int
    timestamp: float


@dataclass(frozen=True, slots=True)
class FrameSnapshot:
    revision: int
    frame: VideoFrameData


class FrameQueue:
    """Bounded queue that favors freshness over preserving stale video frames."""

    def __init__(self, max_size: int = 3) -> None:
        if max_size < 1:
            raise ValueError("Frame queue size must be at least one.")
        self.max_size = max_size
        self._frames: deque[VideoFrameData] = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self.dropped_frames = 0

    def push_latest(self, frame: VideoFrameData) -> None:
        with self._lock:
            if len(self._frames) == self.max_size:
                self.dropped_frames += 1
            self._frames.append(frame)

    def pop_latest(self) -> VideoFrameData | None:
        with self._lock:
            if not self._frames:
                return None
            latest = self._frames[-1]
            if len(self._frames) > 1:
                self.dropped_frames += len(self._frames) - 1
            self._frames.clear()
            return latest

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)
