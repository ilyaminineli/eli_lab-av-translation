from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
from PySide6.QtGui import QImage

import media.thumbnails as thumbnails


class _VideoStream:
    type = "video"


class _Frame:
    def __init__(self, pixels: np.ndarray) -> None:
        self.pixels = pixels

    def to_ndarray(self, format: str) -> np.ndarray:
        assert format == "rgb24"
        return self.pixels


class _Container:
    streams = [_VideoStream()]

    def __init__(self, frame: _Frame) -> None:
        self.frame = frame

    def __enter__(self) -> _Container:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def decode(self, _stream: _VideoStream):
        return iter((self.frame,))


def test_generate_thumbnail_accepts_non_contiguous_rgb_frame(
    tmp_path,
    monkeypatch,
) -> None:
    # A sliced view has gaps between its columns and is not C-contiguous.
    source = np.zeros((36, 64, 3), dtype=np.uint8)
    strided_pixels = source[:, ::2, :]
    assert not strided_pixels.flags.c_contiguous

    fake_container = _Container(_Frame(strided_pixels))
    fake_av = SimpleNamespace(open=lambda _path: fake_container)
    monkeypatch.setitem(sys.modules, "av", fake_av)
    monkeypatch.setattr(thumbnails, "THUMBNAIL_DIR", tmp_path / "thumbnails")

    result = thumbnails.generate_thumbnail(
        "synthetic-source.mp4",
        "strided-frame",
        max_size=(64, 64),
    )

    assert result == tmp_path / "thumbnails" / "strided-frame.jpg"
    assert result.is_file()
    decoded = QImage(str(result))
    assert not decoded.isNull()
    assert decoded.width() <= 64
    assert decoded.height() <= 64
