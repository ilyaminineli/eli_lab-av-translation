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