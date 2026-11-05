from __future__ import annotations

import json

import pytest

from core.performance_environment import (
    MIDIMapping,
    MIDIMappingEngine,
    PerformanceScene,
    PerformanceSetStore,
    SceneMorph,
)


def test_midi_mapping_scales_and_applies_pickup_when_control_crosses_target() -> None:
    engine = MIDIMappingEngine()
    engine.replace_mappings([MIDIMapping(
        mapping_id="macro-energy", device_id="controller", message="cc",
        channel=0, number=16, target="macro.energy", minimum=0.2, maximum=0.8,
        pickup=True,
    )])
    assert engine.process("controller", "cc", 0, 16, 0.1, {"macro.energy": 0.6}) == []
    values = engine.process("controller", "cc", 0, 16, 1.0, {"macro.energy": 0.6})
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


def test_set_save_preserves_baseline_without_mutating_live_layer(tmp_path) -> None:
    from types import SimpleNamespace

    from core.application import Application
    from core.automation import AutomationDirector
    from core.composition import Composition, Layer
    from core.modulation import ModulationMatrix
    from core.modulator_bank import ModulatorBank
    from core.performance_modifiers import LayerPerformanceModifierEngine
    from core.performance_transport import InternalTransport
    from core.project_manager import ProjectManager
    from core.scene_profiles import SceneProfileRegistry
    from effects.settings import EffectSettings

    layer = Layer(
        id='text-layer', source_type='generator', generator_type='text',
        generator_settings={'font_size': 120, 'letter_spacing': 4},
        performance_modifiers=[{'modifier_id': 'one', 'source_id': 'transport.phase',
                               'target_id': 'generator.font_size', 'depth': 0.2}],
    )
    app = Application.__new__(Application)
    app.composition = Composition(layers=[layer])
    app.performance_modifier_engine = LayerPerformanceModifierEngine()
    app.performance_modifier_engine._base_values = {(layer.id, 'generator.font_size'): 120.0}
    app.decks = {}
    app.effects = EffectSettings()
    app.automation = AutomationDirector()
    app.transport = InternalTransport()
    app.audio_capture = SimpleNamespace(settings=SimpleNamespace(to_dict=lambda: {}))
    app.modulation = ModulationMatrix()
    app.scene_profiles = SceneProfileRegistry()
    app.modulator_bank = ModulatorBank()
    app.performance_scenes = {}
    app.midi_mapping_engine = MIDIMappingEngine()
    app.events = SimpleNamespace(publish=lambda *args, **kwargs: None)
    app._selected_layer_id = None
    app._modulation_base_values = {}
    app.project_manager = ProjectManager()
    app.current_project_path = None
    app._generator_modifier_setting_key = Application._generator_modifier_setting_key
    saved = app.save_performance_set(tmp_path / 'text.eliset')
    payload = PerformanceSetStore.load(saved)
    assert payload['composition']['layers'][0]['generator_settings']['font_size'] == 120
    assert layer.generator_settings['font_size'] == 120


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


def test_midi_learn_captures_the_next_matching_controller_event() -> None:
    from types import SimpleNamespace

    from core.application import Application

    app = Application.__new__(Application)
    app._midi_learn_request = {
        "device_id": "controller",
        "target": "macro.energy",
        "minimum": 0.2,
        "maximum": 0.9,
        "curve": "smoothstep",
        "pickup": False,
    }
    app._midi_learn_last_event = ""
    app.midi_mapping_engine = MIDIMappingEngine()
    app.events = SimpleNamespace(publish=lambda *args, **kwargs: None)

    app._handle_midi_event("controller", "cc", 2, 74, 0.5)

    assert app._midi_learn_request is None
    assert len(app.midi_mapping_engine.mappings) == 1
    mapping = app.midi_mapping_engine.mappings[0]
    assert mapping.message == "cc"
    assert mapping.channel == 2
    assert mapping.number == 74
    assert mapping.target == "macro.energy"
    assert mapping.minimum == 0.2
    assert mapping.maximum == 0.9
    assert mapping.curve == "smoothstep"
    assert mapping.pickup is False


def test_quantized_performance_scene_uses_transport_scheduler() -> None:
    from types import SimpleNamespace

    from core.application import Application

    scheduled = []
    app = Application.__new__(Application)
    app.performance_scenes = {
        "drop": PerformanceScene(
            "drop", "Drop", {"composition": {}}, quantization="phrase"
        )
    }
    app._pending_scene_morph_seconds = {}
    app.transport = SimpleNamespace(
        running=True,
        paused=False,
        schedule_scene=lambda *args, **kwargs: scheduled.append((args, kwargs)),
    )
    app.performance_control = SimpleNamespace(intensity=0.75)
    app.events = SimpleNamespace(publish=lambda *args, **kwargs: None)

    assert app.schedule_performance_scene("drop", morph_seconds=2.5) is True
    assert app._pending_scene_morph_seconds["drop"] == 2.5
    assert scheduled[0][0] == ("drop", 0.75)
    assert scheduled[0][1]["quantization"] == "phrase"
