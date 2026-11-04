from __future__ import annotations

import numpy as np

from media.frame_queue import FrameQueue
from media.video_decoder import VideoDecoder


class _PreviewFrame:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.reformat_calls: list[tuple[int, int, str]] = []

    def reformat(self, width: int, height: int, format: str):
        self.reformat_calls.append((width, height, format))
        return _PreviewFrame(width, height)

    def to_ndarray(self, format: str) -> np.ndarray:
        assert format == "rgb24"
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)


def test_preview_pixels_downscale_4k_to_configured_ceiling(tmp_path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"placeholder")
    decoder = VideoDecoder(
        source,
        FrameQueue(),
        max_output_width=1920,
        max_output_height=1080,
    )
    frame = _PreviewFrame(3840, 2160)

    pixels = decoder._preview_pixels(frame)

    assert pixels.shape == (1080, 1920, 3)
    assert frame.reformat_calls == [(1920, 1080, "rgb24")]


def test_preview_pixels_preserve_smaller_sources(tmp_path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"placeholder")
    decoder = VideoDecoder(source, FrameQueue(), max_output_width=1920, max_output_height=1080)
    frame = _PreviewFrame(1280, 720)

    pixels = decoder._preview_pixels(frame)

    assert pixels.shape == (720, 1280, 3)
    assert frame.reformat_calls == []
