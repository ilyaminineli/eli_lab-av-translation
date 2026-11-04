from __future__ import annotations

import moderngl
import numpy as np

from core.composition import Layer
from effects.settings import EffectSettings

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
uniform float u_time;
uniform int u_animation;
uniform float u_animation_speed;
uniform float u_animation_amount;

in vec2 v_uv;
out vec4 frag_color;

void main() {
    vec4 base = texture(u_base, v_uv);
    vec2 screen_uv = vec2(v_uv.x, 1.0 - v_uv.y);
    vec2 animated_position = u_position;
    vec2 animated_scale = u_scale;
    float animated_rotation = u_rotation;
    float animated_opacity = u_opacity;
    float phase = u_time * u_animation_speed;

    if (u_animation == 1) {
        animated_scale *= 1.0 + sin(phase) * u_animation_amount;
    } else if (u_animation == 2) {
        animated_rotation += sin(phase) * u_animation_amount;
    } else if (u_animation == 3) {
        animated_position += vec2(sin(phase), cos(phase * 0.83)) * u_animation_amount;
    } else if (u_animation == 4) {
        animated_opacity *= 0.65 + 0.35 * (0.5 + 0.5 * sin(phase * 3.7));
    }

    vec2 local = screen_uv - animated_position;
    float angle = radians(-animated_rotation);
    float c = cos(angle);
    float s = sin(angle);
    local = vec2(c * local.x - s * local.y, s * local.x + c * local.y);
    local = local / max(animated_scale, vec2(0.001)) + vec2(0.5);

    if (local.x < 0.0 || local.x > 1.0 || local.y < 0.0 || local.y > 1.0) {
        frag_color = base;
        return;
    }

    vec4 source = texture(u_layer, local);
    float alpha = clamp(source.a * animated_opacity, 0.0, 1.0);
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

    frag_color = vec4(mix(base.rgb, blended, alpha), 1.0);
}
"""

_POST_FRAGMENT = """#version 330
uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform float u_time;
uniform float u_brightness;
uniform float u_contrast;
uniform float u_saturation;
uniform float u_gamma;
uniform float u_vignette;
uniform float u_grain;
uniform float u_scanlines;
uniform float u_chromatic;
uniform float u_glitch;
uniform float u_pixelate;
uniform float u_posterize;
uniform float u_invert;

in vec2 v_uv;
out vec4 frag_color;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    vec2 uv = v_uv;

    float row_seed = hash21(vec2(floor(uv.y * u_resolution.y), floor(u_time * 19.0)));
    float glitch_gate = step(0.986, row_seed) * u_glitch;
    uv.x += (row_seed - 0.5) * 0.045 * glitch_gate;

    float pixel_size = mix(1.0, 30.0, clamp(u_pixelate, 0.0, 1.0));
    uv = floor(uv * u_resolution / pixel_size) * pixel_size / u_resolution;
    uv = clamp(uv, vec2(0.001), vec2(0.999));

    vec2 split = vec2(u_chromatic * 0.009 + glitch_gate * 0.012, 0.0);
    vec3 color;
    color.r = texture(u_texture, clamp(uv + split, vec2(0.0), vec2(1.0))).r;
    color.g = texture(u_texture, uv).g;
    color.b = texture(u_texture, clamp(uv - split, vec2(0.0), vec2(1.0))).b;

    color = (color - 0.5) * u_contrast + 0.5;
    float luminance = dot(color, vec3(0.2126, 0.7152, 0.0722));
    color = mix(vec3(luminance), color, u_saturation);
    color = pow(max(color, vec3(0.0)), vec3(1.0 / max(u_gamma, 0.05)));
    color += u_brightness;

    if (u_posterize > 0.001) {
        float levels = mix(24.0, 3.0, clamp(u_posterize, 0.0, 1.0));
        color = floor(clamp(color, 0.0, 1.0) * levels) / levels;
    }
    color = mix(color, vec3(1.0) - color, clamp(u_invert, 0.0, 1.0));

    vec2 centered = (v_uv - 0.5) * vec2(u_resolution.x / max(u_resolution.y, 1.0), 1.0);
    float radius = length(centered);
    float vignette_mask = smoothstep(0.22, 0.92, radius);
    color *= 1.0 - vignette_mask * u_vignette * 0.88;

    float noise_seed = hash21(floor(v_uv * u_resolution) + floor(u_time * 24.0));
    color += (noise_seed - 0.5) * u_grain * 0.22;

    float scan = 0.5 + 0.5 * sin(v_uv.y * u_resolution.y * 3.14159265);
    color *= mix(1.0, 0.72 + 0.28 * scan, u_scanlines);

    frag_color = vec4(clamp(color, 0.0, 1.0), 1.0);
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
    """GPU video-layer compositor followed by a real-time master effects pass."""

    def __init__(self, context: moderngl.Context) -> None:
        self.ctx = context
        self.composite_program = context.program(
            vertex_shader=_VERTEX_SHADER,
            fragment_shader=_COMPOSITE_FRAGMENT,
        )
        self.post_program = context.program(
            vertex_shader=_VERTEX_SHADER,
            fragment_shader=_POST_FRAGMENT,
        )
        vertices = np.array(
            [
                -1.0, -1.0, 0.0, 0.0,
                1.0, -1.0, 1.0, 0.0,
                -1.0, 1.0, 0.0, 1.0,
                1.0, 1.0, 1.0, 1.0,
            ],
            dtype="f4",
        )
        self.vertex_buffer = context.buffer(vertices.tobytes())
        self.composite_vao = context.vertex_array(
            self.composite_program,
            [(self.vertex_buffer, "2f 2f", "in_position", "in_uv")],
        )
        self.post_vao = context.vertex_array(
            self.post_program,
            [(self.vertex_buffer, "2f 2f", "in_position", "in_uv")],
        )
        self.composite_program["u_base"].value = 0
        self.composite_program["u_layer"].value = 1
        self.composite_program["u_animation"].value = 0
        self.composite_program["u_animation_speed"].value = 0.0
        self.composite_program["u_animation_amount"].value = 0.0
        self.post_program["u_texture"].value = 0

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
        if (
                texture is None
                or texture.size != (width, height)
                or texture.components != components
        ):
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

    def _apply_effects(
            self,
            texture: moderngl.Texture,
            target_fbo: int,
            width: int,
            height: int,
            effects: EffectSettings,
            time_seconds: float,
    ) -> None:
        destination = self.ctx.detect_framebuffer(glo=int(target_fbo))
        destination.use()
        self.ctx.viewport = (0, 0, width, height)
        texture.use(location=0)
        effects.clamp()
        values = {
            "u_resolution": (float(width), float(height)),
            "u_time": float(time_seconds),
            "u_brightness": effects.brightness,
            "u_contrast": effects.contrast,
            "u_saturation": effects.saturation,
            "u_gamma": effects.gamma,
            "u_vignette": effects.vignette,
            "u_grain": effects.grain,
            "u_scanlines": effects.scanlines,
            "u_chromatic": effects.chromatic,
            "u_glitch": effects.glitch,
            "u_pixelate": effects.pixelate,
            "u_posterize": effects.posterize,
            "u_invert": effects.invert,
        }
        for uniform_name, value in values.items():
            self.post_program[uniform_name].value = value
        self.post_vao.render(mode=moderngl.TRIANGLE_STRIP)

    def render(
            self,
            layers: list[Layer],
            target_fbo: int,
            width: int,
            height: int,
            effects: EffectSettings | None = None,
            time_seconds: float = 0.0,
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

            self.targets[current].use(location=0)
            layer_texture.use(location=1)

            self.composite_program["u_position"].value = tuple(layer.position)
            self.composite_program["u_scale"].value = tuple(layer.scale)
            self.composite_program["u_rotation"].value = float(layer.rotation)
            self.composite_program["u_opacity"].value = float(layer.opacity)
            self.composite_program["u_blend_mode"].value = _BLEND_MODES.get(
                layer.blend_mode, 0
            )
            self.composite_program["u_time"].value = float(time_seconds)
            animation = layer.generator_settings if layer.source_type == "generator" else {}
            animation_name = str(animation.get("animation", "none"))
            self.composite_program["u_animation"].value = {
                "none": 0,
                "pulse": 1,
                "rotate": 2,
                "drift": 3,
                "flicker": 4,
            }.get(animation_name, 0)
            self.composite_program["u_animation_speed"].value = float(
                animation.get("animation_speed", 0.0)
            )
            self.composite_program["u_animation_amount"].value = float(
                animation.get("animation_amount", 0.0)
            )
            self.composite_vao.render(mode=moderngl.TRIANGLE_STRIP)
            current = next_target

        self._apply_effects(
            self.targets[current],
            target_fbo,
            width,
            height,
            effects or EffectSettings(),
            time_seconds,
        )

    def remove_texture(self, source_id: str) -> None:
        texture = self.source_textures.pop(source_id, None)
        if texture is not None:
            texture.release()

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
        self.post_vao.release()
        self.vertex_buffer.release()
        self.composite_program.release()
        self.post_program.release()
