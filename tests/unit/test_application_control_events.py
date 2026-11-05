from __future__ import annotations

from core.application import Application
from core.composition import Composition
from core.event_bus import EventBus
from core.performance_control import ControlEvent, ControlEventQueue, PerformanceControlState
from core.scene_profiles import SceneProfileRegistry
from effects.settings import EffectSettings


def test_application_drains_control_queue_and_publishes_one_snapshot() -> None:
    application = Application.__new__(Application)
    application.events = EventBus()
    application.control_events = ControlEventQueue()
    application.performance_control = PerformanceControlState()
    application.scene_profiles = SceneProfileRegistry()
    application.effects = EffectSettings()
    application.composition = Composition()
    updates = []
    application.events.subscribe(
        "performance.control.updated",
        lambda **payload: updates.append(payload),
    )

    assert application.submit_control_event(ControlEvent(
        "transport.start",
        "internal-test",
        {"bpm": 92, "beats_per_bar": 4},
    ))
    assert application.submit_control_event(ControlEvent(
        "scene.select",
        "internal-test",
        {"scene_id": "dev", "intensity": 0.62},
    ))

    assert application.process_control_events(max_events=1) == 1
    assert len(updates) == 1
    assert updates[0]["state"]["transport_running"] is True
    assert updates[0]["state"]["scene_id"] == "idle"

    assert application.process_control_events(max_events=8) == 1
    assert len(updates) == 2
    assert updates[-1]["state"]["scene_id"] == "dev"
    assert updates[-1]["state"]["intensity"] == 0.62

def _modulation_application_for_layer(layer):
    from core.automation import AutomationDirector
    from core.modulation import ModulationMatrix

    application = Application.__new__(Application)
    application.events = EventBus()
    application.composition = Composition(layers=[layer])
    application._selected_layer_id = layer.id
    application.effects = EffectSettings()
    application.automation = AutomationDirector()
    application.modulation = ModulationMatrix()
    application._modulation_base_values = {}
    application._overlay_images = {}
    return application


def test_modulation_targets_update_generator_and_text_settings() -> None:
    from core.composition import Layer
    from generators.catalog import default_generator_settings

    geometry = Layer(
        id="geometry-target",
        source_type="generator",
        generator_type="geometry",
        generator_settings=default_generator_settings("geometry"),
    )
    application = _modulation_application_for_layer(geometry)

    assert application._set_modulation_target("generator.animation_speed", 3.5)
    assert geometry.generator_settings["animation_speed"] == 3.5
    assert application._set_modulation_target("generator.density", 28.0)
    assert geometry.generator_settings["density"] == 28

    text_layer = Layer(
        id="text-target",
        source_type="generator",
        generator_type="text",
        generator_settings=default_generator_settings("text"),
    )
    application.composition = Composition(layers=[text_layer])
    application._selected_layer_id = text_layer.id
    assert application._set_modulation_target("generator.text_animation_speed", 5.0)
    assert application._set_modulation_target("generator.text_animation_amount", 0.12)
    assert application._set_modulation_target("generator.font_size", 280.0)
    assert application._set_modulation_target("generator.letter_spacing", 24.0)
    assert text_layer.generator_settings["text_animation_speed"] == 5.0
    assert text_layer.generator_settings["text_animation_amount"] == 0.12
    assert text_layer.generator_settings["font_size"] == 280
    assert text_layer.generator_settings["letter_spacing"] == 24.0


def test_modulation_targets_update_waveform_particles_and_layer_transform() -> None:
    from core.composition import Layer
    from generators.catalog import default_generator_settings

    waveform = Layer(
        id="waveform-target",
        source_type="generator",
        generator_type="waveform",
        generator_settings=default_generator_settings("waveform"),
    )
    application = _modulation_application_for_layer(waveform)
    assert application._set_modulation_target("generator.waveform_amplitude", 0.4)
    assert application._set_modulation_target("generator.waveform_frequency", 12.0)
    assert waveform.generator_settings["amplitude"] == 0.4
    assert waveform.generator_settings["frequency"] == 12.0

    particles = Layer(
        id="particles-target",
        source_type="generator",
        generator_type="particles",
        generator_settings=default_generator_settings("particles"),
    )
    application.composition = Composition(layers=[particles])
    application._selected_layer_id = particles.id
    assert application._set_modulation_target("generator.particle_speed", 1.2)
    assert application._set_modulation_target("generator.particle_size", 0.4)
    assert application._set_modulation_target("generator.particle_spread", 0.8)
    assert application._set_modulation_target("generator.particle_trail", 0.6)
    assert particles.generator_settings["speed"] == 1.2
    assert particles.generator_settings["size"] == 0.4
    assert particles.generator_settings["spread"] == 0.8
    assert particles.generator_settings["trail"] == 0.6

    assert application._set_modulation_target("selected_layer.scale", 1.5)
    assert particles.scale == (1.5, 1.5)
    assert application._set_modulation_target("selected_layer.position_x", 0.25)
    assert particles.position[0] == 0.25


def test_modulation_targets_update_auto_performance_settings() -> None:
    from core.composition import Layer

    application = _modulation_application_for_layer(Layer(id="auto-target"))
    assert application._set_modulation_target("automation.clip_switch_probability", 0.85)
    assert application._set_modulation_target("automation.cut_interval", 12.0)
    assert application._set_modulation_target("automation.min_segment_seconds", 6.0)
    assert application._set_modulation_target("automation.max_segment_seconds", 22.0)
    assert application._set_modulation_target("automation.layout_interval", 18.0)
    assert application._set_modulation_target("automation.effect_interval", 20.0)
    assert application._set_modulation_target("automation.generator_interval", 24.0)
    settings = application.automation.settings
    assert settings.clip_switch_probability == 0.85
    assert settings.min_cut_interval == 12.0
    assert settings.min_segment_seconds == 6.0
    assert settings.max_segment_seconds == 22.0
    assert settings.min_layout_interval == 18.0
    assert settings.min_effect_interval == 20.0
    assert settings.min_generator_interval == 24.0


def test_modulation_targets_update_animated_overlay_playback() -> None:
    from core.composition import Layer

    class AnimatedImageStub:
        animated = True

        def __init__(self):
            self.configured = None

        def configure_playback(self, speed, frame_hold, loop):
            self.configured = (speed, frame_hold, loop)

    overlay = Layer(
        id="animated-overlay-target",
        source_type="overlay",
        source_id="overlay:animated-overlay-target",
        overlay_kind="image",
        overlay_loop=True,
    )
    application = _modulation_application_for_layer(overlay)
    player = AnimatedImageStub()
    application._overlay_images[overlay.id] = player

    assert application._set_modulation_target("overlay.playback_speed", 2.5)
    assert application._set_modulation_target("overlay.frame_hold", 8.0)
    assert overlay.overlay_speed == 2.5
    assert overlay.overlay_frame_hold == 8
    assert player.configured == (2.5, 8, True)


def test_generator_wildcard_manual_override_blocks_reactive_route() -> None:
    import time

    from core.composition import Layer
    from core.modulation import ModulationRoute

    layer = Layer(
        id="generator-manual-override",
        source_type="generator",
        generator_type="geometry",
        generator_settings={"animation_amount": 0.2},
    )
    application = _modulation_application_for_layer(layer)
    application.modulation.add_route(ModulationRoute(
        "audio-to-generator",
        "audio.rms",
        "generator.animation_amount",
        output_min=0.0,
        output_max=0.45,
    ))

    application.notify_manual_override("generator.*", duration_seconds=2.0)
    now = time.monotonic()
    outputs, _released = application.modulation.evaluate({"audio.rms": 1.0}, now=now)
    assert "generator.animation_amount" not in outputs

    outputs, _released = application.modulation.evaluate({"audio.rms": 1.0}, now=now + 3.0)
    assert outputs["generator.animation_amount"] == 0.45

