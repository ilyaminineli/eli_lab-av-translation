from __future__ import annotations

import logging
from pathlib import Path

from config import THUMBNAIL_DIR

_LOG = logging.getLogger(__name__)


def generate_thumbnail(
    video_path: str | Path,
    asset_id: str,
    max_size: tuple[int, int] = (320, 180),
) -> Path | None:
    """Decode one frame and save a cached JPEG thumbnail.

    This function is intended to run in a worker thread. It imports Qt and PyAV
    lazily so metadata-only library tests do not require a GUI application.
    """
    try:
        import av
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
    except ImportError:
        _LOG.debug("Thumbnail dependencies are unavailable.")
        return None

    target = THUMBNAIL_DIR / f"{asset_id}.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        return target

    try:
        with av.open(str(video_path)) as container:
            stream = next((item for item in container.streams if item.type == "video"), None)
            if stream is None:
                return None
            frame = next(container.decode(stream), None)
            if frame is None:
                return None
            pixels = frame.to_ndarray(format="rgb24")
            height, width, _ = pixels.shape
            image = QImage(
                pixels.data,
                width,
                height,
                int(pixels.strides[0]),
                QImage.Format.Format_RGB888,
            ).copy()
            thumbnail = image.scaled(
                max_size[0],
                max_size[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if not thumbnail.save(str(target), "JPG", 88):
                return None
            return target
    except Exception:
        _LOG.exception("Thumbnail generation failed for %s", video_path)
        return None
