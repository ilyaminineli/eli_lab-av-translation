from __future__ import annotations

import json

import pytest

from core.performance_environment import (
    MIDIMapping, MIDIMappingEngine, PerformanceScene,
    PerformanceSetStore, SceneMorph,
)


def test_midi_mapping_scales_and_applies_pickup_when_control_crosses_target() -> None:
    engine = MIDIMappingEngine()
    engine.replace_mappings([MIDIMapping(
        mapping_id="macro-energy", device_id="controller", message="cc",
        channel=0, number=16, target="macro.energy", minimum=0.2, maximum=0.8,
        pickup=True,
    )])
    assert engine.process("controller", "cc", 0, 16, 0.1, {"macro.energy": 0.6}) == []
    values = engine.process("controller", "cc", 0, 16, 0.9, {"macro.energy": 0.6})
    assert values == [("macro.energy", 0.8)]


def test_midi_mapping_without_pickup_has_curve_and_range_scaling() -> None:
    engine = MIDIMappingEngine()
    engine.replace_mappings([MIDIMapping(
        mapping_id="tempo-cc", message="cc", number=7, target="transport.tempo",
        minimum=60, maximum=180, curve="smoothstep", pickup=False,
    )])
    assert engine.process("*", "cc", 0, 7, 0.5) == [("transport.tempo", 120.0)]


def test_midi_mapping_rejects_duplicate_ids_and_invalid_ranges() -> None:
    engine = MIDIMappingEngine()
    with pytest.raises(ValueError):
        engine.replace_mappings([MIDIMapping(mapping_id="same"), MIDIMapping(mapping_id="same")])
    with pytest.raises(ValueError):
        MIDIMapping(minimum=2.0, maximum=1.0).normalize()


def test_scene_morph_interpolates_and_clamps_fraction() -> None:
    morph = SceneMorph({"master.grain": 0.0}, {"master.grain": 1.0}, 10.0, 4.0)
    fraction, values = morph.value(now=12.0)
    assert fraction == 0.5
    assert values["master.grain"] == 0.5
    assert morph.value(now=20.0)[0] == 1.0


def test_performance_set_is_versioned_and_atomically_saved(tmp_path) -> None:
    payload = PerformanceSetStore.build_payload(
        composition={"layers": []}, decks=[], effects={}, automation_settings={},
        performance_settings={},
        scenes=[PerformanceScene("intro", "Intro", {"master.grain": 0.2})],
        midi_mappings=[MIDIMapping(mapping_id="cc1")],
    )
    path = PerformanceSetStore.save(tmp_path / "show.eliset", payload)
    loaded = PerformanceSetStore.load(path)
    assert loaded["format"] == "eli_lab_performance_set"
    assert loaded["version"] == 1
    assert loaded["scenes"][0]["scene_id"] == "intro"
    assert loaded["midi_mappings"][0]["mapping_id"] == "cc1"


def test_performance_set_load_rejects_wrong_format(tmp_path) -> None:
    path = tmp_path / "wrong.eliset"
    path.write_text(json.dumps({"format": "other"}), encoding="utf-8")
    with pytest.raises(ValueError):
        PerformanceSetStore.load(path)

def test_application_performance_set_round_trip_preserves_mapping_bank_and_modifiers(tmp_path) -> None:
    from types import SimpleNamespace

    from core.application import Application
    from core.automation import AutomationDirector
    from core.composition import Composition, Layer
    from core.event_bus import EventBus
    from core.modulation import ModulationMatrix
    from core.modulator_bank import ModulatorBank, ModulatorBankEngine
    from core.performance_modifiers import LayerPerformanceModifier, LayerPerformanceModifierEngine
    from core.performance_transport import InternalTransport
    from core.project_manager import ProjectManager
    from core.scene_profiles import SceneProfileRegistry
    from effects.settings import EffectSettings

    layer = Layer(
        id='particle-set-layer', source_type='generator', generator_type='particles',
        generator_settings={'speed': 0.7, 'size': 0.2},
        performance_modifiers=[LayerPerformanceModifier(
            modifier_id='particle-beat', source_id='transport.beat_pulse',
            target_id='generator.particle_speed', depth=0.2,
        ).to_dict()],
    )
    app = Application.__new__(Application)
    app.events = EventBus()
    app.composition = Composition(layers=[layer])
    app.decks = {'A': SimpleNamespace(to_dict=lambda: {'id': 'A', 'path': None})}
    app.effects = EffectSettings()
    app.automation = AutomationDirector()
    app.transport = InternalTransport()
    app.audio_capture = SimpleNamespace(settings=SimpleNamespace(to_dict=lambda: {}))
    app.modulation = ModulationMatrix()
    app.modulator_bank = ModulatorBank()
    app.performance_modifier_engine = LayerPerformanceModifierEngine()
    app.performance_modifier_engine._base_values[(layer.id, 'generator.particle_speed')] = 0.6
    app.scene_profiles = SceneProfileRegistry()
    app.midi_mapping_engine = MIDIMappingEngine()
    app.midi_mapping_engine.replace_mappings([MIDIMapping(
        mapping_id='cc-energy', target='macro.energy', pickup=False,
    )])
    app.performance_scenes = {}
    app._get_modulation_target = lambda target: None
    app._set_modulation_target = lambda target, value: False
    app._generator_modifier_setting_key = Application._generator_modifier_setting_key
    app._handle_midi_event = lambda *args: None
    app.project_manager = ProjectManager()
    app._selected_layer_id = None
    app._modulation_base_values = {}
    app._clear_overlays = lambda: None
    app._attach_overlay_layer = lambda layer: None
    app.layer_manager = SimpleNamespace()
    app._audio_sources = {}
    app._latest_audio_frame = None
    app.control_events = SimpleNamespace(clear=lambda: None)
    app.performance_control = SimpleNamespace(reset=lambda: None, bpm=120.0, beats_per_bar=4)
    app._external_clock_bar_at = None
    app.osc_receiver = SimpleNamespace(stop=lambda: None)
    app.transport.stop = lambda: None
    app.audio_capture.stop = lambda: None
    app.audio_capture.shutdown = lambda: None
    app.modulation.reset_runtime = lambda: None
    app.performance_modifier_engine.reset = lambda: None
    app.modulator_bank_engine = ModulatorBankEngine()
    app.decks['A'].close = lambda: None
    app.decks['A'].locked = False
    app._frame_snapshots = {}
    app._overlay_images = {}
    app._overlay_videos = {}
    app._overlay_frames = {}
    app._overlay_started_at = {}
    app._automation_collection_id = None
    app.current_project_path = None
    app.events.publish = lambda *args, **kwargs: None
    app.midi_input = SimpleNamespace(stop=lambda: None)
    app.update_audio_analysis_settings = lambda settings: None
    app.automation.settings.normalize()
    app._create_default_layers = lambda: None
    app._midi_target_values = lambda: {}
    app._modulation_sources = lambda: {}
    app.audio_analysis_snapshot = lambda: {}
    app.apply_modulation = lambda: {}
    app.process_audio_frames = lambda: 0
    app.submit_control_event = lambda event: True
    app.performance_control = SimpleNamespace(reset=lambda: None, bpm=120.0, beats_per_bar=4)
    app.transport.load_settings = lambda value: None
    app.scene_profiles = SceneProfileRegistry()
    app._automation_collection_id = None
    app.current_project_path = None
    app.load_project = Application.load_project.__get__(app)
    app.save_performance_set = Application.save_performance_set.__get__(app)
    app.load_performance_set = Application.load_performance_set.__get__(app)
    app.transport = InternalTransport()
    app.automation.stop = lambda: None
    app.audio_capture.update_settings = lambda settings: None
    app.performance_control = SimpleNamespace(reset=lambda: None, bpm=120.0, beats_per_bar=4)
    app.performance_modifier_engine.reset = lambda: None
    app._clear_overlays = lambda: None
    app._attach_overlay_layer = lambda layer: None
    app.project_manager = ProjectManager()
    app.performance_modifier_engine.base_values = lambda: {(layer.id, 'generator.particle_speed'): 0.6}
    app.midi_mapping_engine.mappings[0].normalize()

    destination = app.save_performance_set(tmp_path / 'show.eliset')
    payload = PerformanceSetStore.load(destination)
    assert payload['composition']['layers'][0]['generator_settings']['speed'] == 0.6
    assert payload['midi_mappings'][0]['mapping_id'] == 'cc-energy'


def test_midi_input_service_queue_is_bounded_and_drain_is_deferred() -> None:
    from types import SimpleNamespace
    from core.performance_environment import MIDIInputService

    seen = []
    service = MIDIInputService(lambda *event: seen.append(event), queue_capacity=1)
    message = SimpleNamespace(type='control_change', channel=0, control=7, value=64)
    service._receive('device', message)
    service._receive('device', message)
    assert service.dropped_events == 1
    assert seen == []
    assert service.drain() == 1
    assert len(seen) == 1

