from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from media.frame_queue import FrameQueue, VideoFrameData

_LOG = logging.getLogger(__name__)


class VideoDecoder:
    """Timestamp-paced PyAV decoder with optional random in/out segment looping."""

    def __init__(
        self,
        path: str | Path,
        frame_queue: FrameQueue,
        loop: bool = True,
        segment_start: float = 0.0,
        segment_end: float | None = None,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.frame_queue = frame_queue
        self.loop = bool(loop)
        self.segment_start = max(0.0, float(segment_start))
        self.segment_end = (
            max(self.segment_start + 0.05, float(segment_end))
            if segment_end is not None else None
        )
        self._condition = threading.Condition()
        self._thread: threading.Thread | None = None
        self._running = False
        self._playing = False
        self._seek_request: float | None = None
        self._paused_at: float | None = None
        self._timeline_shift = 0.0
        self._last_error: str | None = None

    @property
    def is_playing(self) -> bool:
        with self._condition:
            return self._playing and self._running

    @property
    def is_running(self) -> bool:
        with self._condition:
            return self._running

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def start(self, autoplay: bool = True) -> None:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        with self._condition:
            if self._thread and self._thread.is_alive():
                self._playing = autoplay
                self._condition.notify_all()
                return
            self._running = True
            self._playing = autoplay
            self._seek_request = None
            self._paused_at = None
            self._timeline_shift = 0.0
            self._last_error = None
            self._thread = threading.Thread(
                target=self._decode_loop,
                name=f"VideoDecoder-{self.path.name}",
                daemon=True,
            )
            self._thread.start()

    def play(self) -> None:
        with self._condition:
            if self._paused_at is not None:
                self._timeline_shift += time.monotonic() - self._paused_at
                self._paused_at = None
            self._playing = True
            self._condition.notify_all()

    def pause(self) -> None:
        with self._condition:
            if self._playing:
                self._paused_at = time.monotonic()
            self._playing = False
            self._condition.notify_all()

    def seek(self, seconds: float) -> None:
        with self._condition:
            self._seek_request = max(0.0, float(seconds))
            self.frame_queue.clear()
            self._condition.notify_all()

    def set_loop(self, enabled: bool) -> None:
        with self._condition:
            self.loop = bool(enabled)

    def stop(self, timeout: float = 2.0) -> None:
        with self._condition:
            self._running = False
            self._playing = False
            self._condition.notify_all()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None
        self.frame_queue.clear()

    def _wait_for_deadline(self, deadline: float) -> str:
        with self._condition:
            while self._running:
                if self._seek_request is not None:
                    return "seek"
                if not self._playing:
                    self._condition.wait(timeout=0.1)
                    continue
                remaining = deadline + self._timeline_shift - time.monotonic()
                if remaining <= 0:
                    return "frame"
                self._condition.wait(timeout=min(remaining, 0.05))
        return "stop"

    def _take_seek_request(self, default: float) -> float:
        with self._condition:
            if self._seek_request is None:
                return default
            value = self._seek_request
            self._seek_request = None
            self._timeline_shift = 0.0
            self._paused_at = None
            return value

    def _decode_loop(self) -> None:
        try:
            import av
        except ImportError:
            self._last_error = "PyAV is not installed."
            with self._condition:
                self._running = False
                self._playing = False
            return

        seek_to = self.segment_start
        while True:
            with self._condition:
                if not self._running:
                    break
            try:
                with av.open(str(self.path)) as container:
                    stream = next(
                        (item for item in container.streams if item.type == "video"),
                        None,
                    )
                    if stream is None:
                        raise ValueError("No video stream was found.")
                    if seek_to > 0 and stream.time_base:
                        container.seek(
                            int(seek_to / float(stream.time_base)),
                            stream=stream,
                            backward=True,
                        )

                    average_rate = float(stream.average_rate) if stream.average_rate else 30.0
                    first_timestamp: float | None = None
                    timeline_start = 0.0
                    frame_index = 0
                    restart = False

                    for frame in container.decode(stream):
                        with self._condition:
                            if not self._running:
                                return
                            pending_seek = self._seek_request
                        if pending_seek is not None:
                            seek_to = self._take_seek_request(seek_to)
                            restart = True
                            break

                        if frame.pts is not None and stream.time_base:
                            timestamp = float(frame.pts * stream.time_base)
                        else:
                            timestamp = frame_index / max(average_rate, 0.1)
                        frame_index += 1

                        if timestamp + 0.03 < seek_to:
                            continue
                        if self.segment_end is not None and timestamp >= self.segment_end:
                            break

                        if first_timestamp is None:
                            first_timestamp = timestamp
                            timeline_start = time.monotonic()

                        due = timeline_start + (timestamp - first_timestamp)
                        wait_result = self._wait_for_deadline(due)
                        if wait_result == "stop":
                            return
                        if wait_result == "seek":
                            seek_to = self._take_seek_request(seek_to)
                            restart = True
                            break

                        pixels = frame.to_ndarray(format="rgb24")
                        height, width, _ = pixels.shape
                        self.frame_queue.push_latest(
                            VideoFrameData(
                                pixels=pixels,
                                width=int(width),
                                height=int(height),
                                timestamp=timestamp,
                            )
                        )

                if restart:
                    continue
                with self._condition:
                    should_loop = self.loop
                if should_loop:
                    seek_to = self.segment_start
                    continue
                with self._condition:
                    self._playing = False
                    self._running = False
                break
            except Exception as exc:
                self._last_error = str(exc)
                _LOG.exception("Video decoding failed: %s", self.path)
                with self._condition:
                    self._playing = False
                    self._running = False
                break
