import numpy as np

from media.frame_queue import FrameQueue, VideoFrameData


def make_frame(timestamp: float) -> VideoFrameData:
    pixels = np.zeros((2, 3, 3), dtype=np.uint8)
    return VideoFrameData(pixels, width=3, height=2, timestamp=timestamp)


def test_frame_queue_returns_newest_frame() -> None:
    queue = FrameQueue(max_size=2)
    queue.push_latest(make_frame(1.0))
    queue.push_latest(make_frame(2.0))
    queue.push_latest(make_frame(3.0))
    latest = queue.pop_latest()
    assert latest is not None
    assert latest.timestamp == 3.0
    assert queue.dropped_frames >= 1
    assert len(queue) == 0


def test_empty_queue_returns_none() -> None:
    assert FrameQueue().pop_latest() is None
