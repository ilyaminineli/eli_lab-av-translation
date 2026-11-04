from __future__ import annotations

import logging

import moderngl
import numpy as np

from core.composition import Layer

_LOG = logging.getLogger(__name__)

_VERTEX_SHADER = """#version 330
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

_COMPOSITE_FRAGMENT = """#version 330
uniform sampler2D u_base;
uniform sampler2D u_layer;
uniform vec2 u_position;
uniform vec2 u_scale;
uniform float u_rotation;
uniform float u_opacity;
uniform int u_blend_mode;

in vec2 v_uv;
out vec4 frag_color;

void main() {
    vec4 base = texture(u_base, v_uv);

    vec2 screen_uv = vec2(v_uv.x, 1.0 - v_uv.y);
    vec2 local = screen_uv - u_position;
    float angle = radians(-u_rotation);
    float c = cos(angle);
    float s = sin(angle);
    local = vec2(c * local.x - s * local.y, s * local.x + c * local.y);
    local = local / max(u_scale, vec2(0.001)) + vec2(0.5);

    if (local.x < 0.0 || local.x > 1.0 || local.y < 0.0 || local.y > 1.0) {
        frag_color = base;
        return;
    }

    vec4 source = texture(u_layer, local);
    float alpha = clamp(source.a * u_opacity, 0.0, 1.0);
    vec3 blended = source.rgb;

    if (u_blend_mode == 1) {
        blended = min(base.rgb + source.rgb, vec3(1.0));
    } else if (u_blend_mode == 2) {
        blended = 1.0 - (1.0 - base.rgb) * (1.0 - source.rgb);
    } else if (u_blend_mode == 3) {
        blended = base.rgb * source.rgb;
    } else if (u_blend_mode == 4) {
        blended = abs(base.rgb - source.rgb);
    }

    frag_color = vec4(mix(base.rgb, blended, alpha), alpha + base.a * (1.0 - alpha));
}
"""

_DISPLAY_FRAGMENT = """#version 330
uniform sampler2D u_texture;
in vec2 v_uv;
out vec4 frag_color;
void main() {
    frag_color = texture(u_texture, v_uv);
}
"""

_BLEND_MODES = {
    "normal": 0,
    "add": 1,
    "screen": 2,
    "multiply": 3,
    "difference": 4,
}


class Compositor:
    """Two-pass, texture-based layer compositor.

    Decoded video frames are uploaded on the render thread. Every composition
    pass reads the previous framebuffer and blends one transformed layer into
    the other framebuffer (ping-pong), avoiding CPU readback.
    """

    def __init__(self, context: moderngl.Context) -> None:
        self.ctx = context
        self.composite_program = context.program(
            vertex_shader=_VERTEX_SHADER,
            fragment_shader=_COMPOSITE_FRAGMENT,
        )
        self.display_program = context.program(
            vertex_shader=_VERTEX_SHADER,
            fragment_shader=_DISPLAY_FRAGMENT,
        )
        vertices = np.array(
            [
                -1.0, -1.0, 0.0, 0.0,
                 1.0, -1.0, 1.0, 0.0,
                -1.0,  1.0, 0.0, 1.0,
                 1.0,  1.0, 1.0, 1.0,
            ],
            dtype="f4",
        )
        self.vertex_buffer = context.buffer(vertices.tobytes())
        self.composite_vao = context.vertex_array(
            self.composite_program,
            [(self.vertex_buffer, "2f 2f", "in_position", "in_uv")],
        )
        self.display_vao = context.vertex_array(
            self.display_program,
            [(self.vertex_buffer, "2f 2f", "in_position", "in_uv")],
        )
        self.composite_program["u_base"].value = 0
        self.composite_program["u_layer"].value = 1
        self.display_program["u_texture"].value = 0

        self.source_textures: dict[str, moderngl.Texture] = {}
        self.targets: list[moderngl.Texture] = []
        self.framebuffers: list[moderngl.Framebuffer] = []
        self.size = (0, 0)

    def update_texture(self, source_id: str, pixels: np.ndarray) -> None:
        frame = np.ascontiguousarray(pixels, dtype=np.uint8)
        if frame.ndim != 3 or frame.shape[2] not in (3, 4):
            raise ValueError("Video texture must be an HxWx3 or HxWx4 uint8 array.")
        height, width, components = frame.shape
        texture = self.source_textures.get(source_id)
        if texture is None or texture.size != (width, height) or texture.components != components:
            if texture is not None:
                texture.release()
            texture = self.ctx.texture(
                (width, height),
                components,
                frame.tobytes(),
                alignment=1,
                dtype="f1",
            )
            texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            texture.repeat_x = False
            texture.repeat_y = False
            self.source_textures[source_id] = texture
        else:
            texture.write(frame.tobytes(), alignment=1)

    def _resize_targets(self, width: int, height: int) -> None:
        width = max(1, int(width))
        height = max(1, int(height))
        if self.size == (width, height):
            return
        self._release_targets()
        for _ in range(2):
            texture = self.ctx.texture((width, height), 4, dtype="f1")
            texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            framebuffer = self.ctx.framebuffer(color_attachments=[texture])
            self.targets.append(texture)
            self.framebuffers.append(framebuffer)
        self.size = (width, height)

    def render(
        self,
        layers: list[Layer],
        target_fbo: int,
        width: int,
        height: int,
    ) -> None:
        self._resize_targets(width, height)
        self.ctx.viewport = (0, 0, width, height)
        self.framebuffers[0].use()
        self.framebuffers[0].clear(0.025, 0.028, 0.035, 1.0)

        current = 0
        for layer in sorted(layers, key=lambda item: item.z_index):
            if not layer.visible or layer.opacity <= 0.0:
                continue
            layer_texture = self.source_textures.get(layer.source_id)
            if layer_texture is None:
                continue

            next_target = 1 - current
            self.framebuffers[next_target].use()
            self.ctx.viewport = (0, 0, width, height)

            base_texture = self.targets[current]
            base_texture.use(location=0)
            layer_texture.use(location=1)

            self.composite_program["u_position"].value = tuple(layer.position)
            self.composite_program["u_scale"].value = tuple(layer.scale)
            self.composite_program["u_rotation"].value = float(layer.rotation)
            self.composite_program["u_opacity"].value = float(layer.opacity)
            self.composite_program["u_blend_mode"].value = _BLEND_MODES.get(
                layer.blend_mode, 0
            )
            self.composite_vao.render(mode=moderngl.TRIANGLE_STRIP)
            current = next_target

        destination = self.ctx.detect_framebuffer(glo=int(target_fbo))
        destination.use()
        self.ctx.viewport = (0, 0, width, height)
        self.targets[current].use(location=0)
        self.display_vao.render(mode=moderngl.TRIANGLE_STRIP)

    def _release_targets(self) -> None:
        for framebuffer in self.framebuffers:
            framebuffer.release()
        for texture in self.targets:
            texture.release()
        self.framebuffers.clear()
        self.targets.clear()

    def release(self) -> None:
        self._release_targets()
        for texture in self.source_textures.values():
            texture.release()
        self.source_textures.clear()
        self.composite_vao.release()
        self.display_vao.release()
        self.vertex_buffer.release()
        self.composite_program.release()
        self.display_program.release()
