from __future__ import annotations

import logging
import time
from typing import Any

from config import OPENGL_REQUIREMENT
from core.composition import Composition
from effects.settings import EffectSettings
from rendering.compositor import Compositor

_LOG = logging.getLogger(__name__)


class RenderEngine:
    """Owns per-window ModernGL resources and renders a shared composition snapshot."""

    def __init__(self) -> None:
        self.context: Any | None = None
        self.compositor: Compositor | None = None
        self.initialized = False
        self.renderer_name = "Not initialized"
        self.version_code = 0
        self._uploaded_revisions: dict[str, int] = {}

    def initialize(self) -> None:
        try:
            import moderngl
        except ImportError as exc:
            raise RuntimeError(
                "ModernGL is not installed. Install requirements-dev.txt or requirements.txt."
            ) from exc

        # QOpenGLWidget.initializeGL makes Qt's context current before this call.
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
            effects: EffectSettings | None = None,
    ) -> None:
        if not self.initialized or self.compositor is None:
            return
        for source_id, snapshot in frames.items():
            revision = int(getattr(snapshot, "revision", -1))
            if revision >= 0 and self._uploaded_revisions.get(source_id) == revision:
                continue
            frame = getattr(snapshot, "frame", snapshot)
            pixels = getattr(frame, "pixels", None)
            if pixels is not None:
                self.compositor.update_texture(source_id, pixels)
                if revision >= 0:
                    self._uploaded_revisions[source_id] = revision
        self.compositor.render(
            composition.layers,
            target_fbo,
            width,
            height,
            effects=effects,
            time_seconds=time.perf_counter(),
        )

    def release(self) -> None:
        if self.compositor is not None:
            self.compositor.release()
            self.compositor = None
        self._uploaded_revisions.clear()
        self.context = None
        self.initialized = False
