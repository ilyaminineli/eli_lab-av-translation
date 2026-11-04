from __future__ import annotations

import logging
from typing import Any

from config import OPENGL_REQUIREMENT
from core.composition import Composition
from rendering.compositor import Compositor

_LOG = logging.getLogger(__name__)


class RenderEngine:
    """Owns ModernGL resources and renders a composition into a Qt FBO."""

    def __init__(self) -> None:
        self.context: Any | None = None
        self.compositor: Compositor | None = None
        self.initialized = False
        self.renderer_name = "Not initialized"
        self.version_code = 0

    def initialize(self) -> None:
        try:
            import moderngl
        except ImportError as exc:
            raise RuntimeError(
                "ModernGL is not installed. Run: pip install -e '.[dev]'"
            ) from exc

        # Called from QOpenGLWidget.initializeGL(), when Qt has made its context current.
        self.context = moderngl.create_context(require=OPENGL_REQUIREMENT)
        self.compositor = Compositor(self.context)
        info = self.context.info
        self.renderer_name = str(info.get("GL_RENDERER", "Unknown renderer"))
        self.version_code = int(info.get("GL_VERSION_CODE", 0))
        self.initialized = True
        _LOG.info(
            "OpenGL initialized: %s (version code %s)",
            self.renderer_name,
            self.version_code,
        )

    def render(
        self,
        composition: Composition,
        frames: dict[str, object],
        target_fbo: int,
        width: int,
        height: int,
    ) -> None:
        if not self.initialized or self.compositor is None:
            return
        for source_id, frame in frames.items():
            pixels = getattr(frame, "pixels", None)
            if pixels is not None:
                self.compositor.update_texture(source_id, pixels)
        self.compositor.render(composition.layers, target_fbo, width, height)

    def release(self) -> None:
        if self.compositor is not None:
            self.compositor.release()
            self.compositor = None
        self.context = None
        self.initialized = False
