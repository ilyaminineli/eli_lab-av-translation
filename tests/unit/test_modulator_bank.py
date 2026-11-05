from __future__ import annotations

import pytest

from core.modulator_bank import (
    ModulatorBank,
    ModulatorBankEngine,
    ModulatorDefinition,
)


def _transport_sources(beat_position: float, running: bool = True) -> dict[str, float]:
    return {
        "transport.running": 1.0 if running else 0.0,
        "transport.beat_position": beat_position,
        "transport.beats_per_bar": 4.0,
        "transport.phrase_beats": 16.0,
        "transport.beat_pulse": 1.0 if beat_position % 1.0 < 0.1 else 0.0,
        "transport.downbeat_pulse": (
            1.0 if beat_position % 4.0 < 0.1 else 0.0
        ),
        "transport.phrase_pulse": (
            1.0 if beat_position % 16.0 < 0.1 else 0.0
        ),
        "audio.onset": 0.0,
        "audio.peak": 0.0,
        "macro.energy": 0.0,
    }


def _bank_with(definition: ModulatorDefinition) -> ModulatorBank:
    bank = ModulatorBank()
    bank.add(definition)
    return bank


def test_builtin_modulator_presets_cover_all_four_kinds() -> None:
    bank = ModulatorBank()

    kinds = {
        ModulatorDefinition.from_dict(preset.definition).kind
        for preset in bank.list_presets()
    }

    assert {"envelope", "lfo", "steps", "rhythm"}.issubset(kinds)
    assert len(bank.list_presets()) >= 8


def test_user_presets_and_active_modulators_survive_bank_round_trip() -> None:
    bank = ModulatorBank()
    definition = bank.instantiate_preset("lfo-sine-swell")
    saved_preset_id = bank.save_preset(
        definition.modulator_id,
        "Eli slow orbit",
        "A custom four-bar oscillator.",
    )
    payload = bank.to_dict()

    restored = ModulatorBank()
    restored.load_dict(payload)

    assert restored.get(definition.modulator_id) is not None
    preset = restored.presets[saved_preset_id]
    assert preset.name == "Eli slow orbit"
    assert preset.builtin is False
    assert restored.delete_preset(saved_preset_id)
    assert not restored.delete_preset("lfo-sine-swell")


def test_modulator_definition_clamps_rates_and_normalizes_step_values() -> None:
    definition = ModulatorDefinition(
        kind="steps",
        rate_beats=0.0,
        rate_hz=100.0,
        step_values=[-1.0, 0.25, 2.0],
        division_beats=0.0,
        swing=0.9,
    )
    definition.normalize()

    assert definition.rate_beats == 0.0625
    assert definition.rate_hz == 30.0
    assert definition.step_values == [0.0, 0.25, 1.0]
    assert definition.division_beats == pytest.approx(1.0 / 96.0)
    assert definition.swing == 0.75


def test_lfo_tracks_transport_beats_and_has_a_centered_sine_cycle() -> None:
    definition = ModulatorDefinition(
        modulator_id="sine-four",
        kind="lfo",
        waveform="sine",
        rate_beats=4.0,
        sync_mode="transport",
    )
    bank = _bank_with(definition)
    engine = ModulatorBankEngine()

    at_zero = engine.evaluate(bank, _transport_sources(0.0), now=10.0)
    at_quarter = engine.evaluate(bank, _transport_sources(1.0), now=10.25)
    at_half = engine.evaluate(bank, _transport_sources(2.0), now=10.5)
    at_three_quarter = engine.evaluate(
        bank, _transport_sources(3.0), now=10.75
    )

    assert at_zero["modulator.sine-four"] == pytest.approx(0.5)
    assert at_quarter["modulator.sine-four"] == pytest.approx(1.0)
    assert at_half["modulator.sine-four"] == pytest.approx(0.5)
    assert at_three_quarter["modulator.sine-four"] == pytest.approx(0.0)


def test_free_running_lfo_uses_hz_without_transport() -> None:
    definition = ModulatorDefinition(
        modulator_id="free-triangle",
        kind="lfo",
        waveform="triangle",
        sync_mode="free",
        rate_hz=0.25,
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    first = engine.evaluate(bank, {}, now=100.0)
    second = engine.evaluate(bank, {}, now=101.0)
    third = engine.evaluate(bank, {}, now=102.0)

    assert first["modulator.free-triangle"] == pytest.approx(0.0)
    assert second["modulator.free-triangle"] == pytest.approx(0.5)
    assert third["modulator.free-triangle"] == pytest.approx(1.0)


def test_adsr_envelope_responds_to_trigger_and_releases_in_beat_time() -> None:
    definition = ModulatorDefinition(
        modulator_id="test-adsr",
        kind="envelope",
        sync_mode="transport",
        trigger_source="transport.beat_pulse",
        attack=0.5,
        decay=0.5,
        sustain=0.2,
        gate=2.0,
        release=1.0,
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    trigger = _transport_sources(0.0)
    trigger["transport.beat_pulse"] = 1.0
    attack_mid = _transport_sources(0.25)
    decay_mid = _transport_sources(0.75)
    sustain = _transport_sources(1.5)
    release_mid = _transport_sources(2.5)
    finished = _transport_sources(3.1)

    assert engine.evaluate(bank, trigger, now=0.0)["modulator.test-adsr"] == 0.0
    assert engine.evaluate(bank, attack_mid, now=0.25)["modulator.test-adsr"] == pytest.approx(0.5)
    assert engine.evaluate(bank, decay_mid, now=0.75)["modulator.test-adsr"] == pytest.approx(0.6)
    assert engine.evaluate(bank, sustain, now=1.5)["modulator.test-adsr"] == pytest.approx(0.2)
    assert engine.evaluate(bank, release_mid, now=2.5)["modulator.test-adsr"] == pytest.approx(0.1)
    assert engine.evaluate(bank, finished, now=3.1)["modulator.test-adsr"] == 0.0


def test_envelope_uses_audio_onset_in_free_timebase() -> None:
    definition = ModulatorDefinition(
        modulator_id="audio-env",
        kind="envelope",
        sync_mode="free",
        trigger_source="audio.onset",
        attack=0.0,
        decay=0.0,
        sustain=1.0,
        gate=0.0,
        release=1.0,
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    onset = {"audio.onset": 1.0}
    tail = {"audio.onset": 0.0}

    assert engine.evaluate(bank, onset, now=5.0)["modulator.audio-env"] == 1.0
    assert engine.evaluate(bank, tail, now=5.5)["modulator.audio-env"] == pytest.approx(0.5)
    assert engine.evaluate(bank, tail, now=6.1)["modulator.audio-env"] == 0.0


def test_rhythm_pattern_produces_centered_off_steps_and_gated_accents() -> None:
    definition = ModulatorDefinition(
        modulator_id="kick-grid",
        kind="rhythm",
        step_values=[1.0, 0.0, 0.5, 0.0],
        division_beats=0.25,
        pulse_width=0.4,
        sync_mode="transport",
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    first_step = engine.evaluate(
        bank, _transport_sources(0.0), now=1.0
    )["modulator.kick-grid"]
    first_step_tail = engine.evaluate(
        bank, _transport_sources(0.15), now=1.15
    )["modulator.kick-grid"]
    off_step = engine.evaluate(
        bank, _transport_sources(0.25), now=1.25
    )["modulator.kick-grid"]
    third_step = engine.evaluate(
        bank, _transport_sources(0.5), now=1.5
    )["modulator.kick-grid"]

    assert first_step == pytest.approx(1.0)
    assert first_step_tail == pytest.approx(0.5)
    assert off_step == pytest.approx(0.5)
    assert third_step == pytest.approx(0.75)


def test_step_sequence_supports_interpolation_and_reverse_direction() -> None:
    definition = ModulatorDefinition(
        modulator_id="linear-steps",
        kind="steps",
        step_values=[0.0, 1.0],
        division_beats=1.0,
        interpolation="linear",
        sync_mode="transport",
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    middle = engine.evaluate(
        bank, _transport_sources(0.5), now=1.0
    )["modulator.linear-steps"]
    assert middle == pytest.approx(0.5)

    definition.direction = "reverse"
    bank.update(definition)
    engine.reset_modulator(definition.modulator_id)
    reverse_start = engine.evaluate(
        bank, _transport_sources(0.0), now=2.0
    )["modulator.linear-steps"]
    assert reverse_start == pytest.approx(1.0)


def test_swing_delays_the_second_step_of_each_pair() -> None:
    definition = ModulatorDefinition(
        modulator_id="swing-grid",
        kind="steps",
        step_values=[0.0, 1.0],
        division_beats=0.5,
        interpolation="hold",
        swing=0.67,
        sync_mode="transport",
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    first = engine.evaluate(
        bank, _transport_sources(0.6), now=1.0
    )["modulator.swing-grid"]
    second = engine.evaluate(
        bank, _transport_sources(0.8), now=1.2
    )["modulator.swing-grid"]

    assert first == pytest.approx(0.0)
    assert second == pytest.approx(1.0)


def test_transport_stopped_lfo_returns_neutral_center() -> None:
    definition = ModulatorDefinition(
        modulator_id="stopped-lfo",
        kind="lfo",
        waveform="sine",
        sync_mode="transport",
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    values = engine.evaluate(bank, _transport_sources(2.0, running=False), now=10.0)

    assert values["modulator.stopped-lfo"] == pytest.approx(0.5)


def test_bypassed_modulator_is_omitted_from_active_source_set() -> None:
    definition = ModulatorDefinition(
        modulator_id="bypassed",
        kind="lfo",
        enabled=False,
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    assert engine.evaluate(bank, _transport_sources(0.0), now=1.0) == {}
    assert engine.live_values() == {}


def test_modulator_engine_prunes_removed_sources() -> None:
    definition = ModulatorDefinition(
        modulator_id="temporary-source",
        kind="lfo",
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)
    engine.evaluate(bank, _transport_sources(0.0), now=1.0)

    bank.remove(definition.modulator_id)
    engine.evaluate(bank, _transport_sources(1.0), now=2.0)

    assert engine.live_values() == {}
    assert definition.modulator_id not in engine._runtime

def test_bank_lfo_can_drive_existing_per_layer_modifier_target() -> None:
    from core.application import Application
    from core.composition import Composition, Layer
    from core.modulation import ModulationMatrix
    from core.performance_modifiers import (
        LayerPerformanceModifier,
        LayerPerformanceModifierEngine,
    )

    definition = ModulatorDefinition(
        modulator_id="app-lfo",
        kind="lfo",
        waveform="sine",
        rate_beats=4.0,
        sync_mode="transport",
    )
    bank = _bank_with(definition)
    layer = Layer(
        id="bank-driven-geometry",
        source_type="generator",
        generator_type="geometry",
        generator_settings={"animation_amount": 12.0},
        performance_modifiers=[LayerPerformanceModifier(
            modifier_id="bank-route",
            source_id="modulator.app-lfo",
            target_id="generator.animation_amount",
            depth=0.1,
            polarity="bipolar",
            curve="linear",
        ).to_dict()],
    )
    application = Application.__new__(Application)
    application.composition = Composition(layers=[layer])
    application._selected_layer_id = layer.id
    application.modulator_bank = bank
    application.modulator_bank_engine = ModulatorBankEngine()
    application.performance_modifier_engine = LayerPerformanceModifierEngine()
    application.modulation = ModulationMatrix()
    application._modulation_base_values = {}
    application._modulation_sources = lambda: _transport_sources(1.0)

    application.apply_modulation()

    assert layer.generator_settings["animation_amount"] == pytest.approx(48.0)

    # Bypassing the bank source drops ownership and restores the pre-modulation base.
    disabled = bank.get("app-lfo")
    assert disabled is not None
    disabled.enabled = False
    bank.update(disabled)
    application.apply_modulation()

    assert layer.generator_settings["animation_amount"] == pytest.approx(12.0)

def test_user_presets_can_be_exported_and_imported_between_banks(tmp_path) -> None:
    source_bank = ModulatorBank()
    active = source_bank.instantiate_preset("seq-clave-3-2")
    source_bank.save_preset(active.modulator_id, "My clave")
    path = tmp_path / "modulators.json"

    assert source_bank.export_presets(path) == path

    target_bank = ModulatorBank()
    imported = target_bank.import_presets(path)

    assert imported == 1
    imported_preset = next(
        preset for preset in target_bank.list_presets()
        if preset.name == "My clave"
    )
    clone = target_bank.instantiate_preset(imported_preset.preset_id)
    assert clone.kind == "rhythm"
    assert clone.step_values == active.step_values

def test_pingpong_sequence_runs_forward_then_backward_before_looping() -> None:
    definition = ModulatorDefinition(
        modulator_id="pingpong-grid",
        kind="steps",
        step_values=[0.0, 0.5, 1.0],
        division_beats=1.0,
        interpolation="hold",
        direction="pingpong",
        swing=0.5,
    )
    engine = ModulatorBankEngine()
    bank = _bank_with(definition)

    values = [
        engine.evaluate(
            bank, _transport_sources(beat), now=float(beat)
        )["modulator.pingpong-grid"]
        for beat in range(5)
    ]

    assert values == pytest.approx([0.0, 0.5, 1.0, 0.5, 0.0])

