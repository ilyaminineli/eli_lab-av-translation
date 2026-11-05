from __future__ import annotations

from core.composition import Layer
from core.performance_modifiers import (
    LayerPerformanceModifier,
    LayerPerformanceModifierEngine,
)


def _memory_target_store(initial: dict[str, dict[str, float]]):
    values = {layer_id: dict(targets) for layer_id, targets in initial.items()}

    def get_target(layer_id: str, target_id: str) -> float | None:
        return values.get(layer_id, {}).get(target_id)

    def set_target(layer_id: str, target_id: str, value: float) -> bool:
        if layer_id not in values or target_id not in values[layer_id]:
            return False
        values[layer_id][target_id] = value
        return True

    return values, get_target, set_target


def test_modifier_normalizes_source_depth_curve_and_serializes() -> None:
    modifier = LayerPerformanceModifier(
        name="  Beat swell  ",
        source_id="transport.beat_pulse",
        target_id="generator.animation_amount",
        depth=1.8,
        polarity="invalid",  # type: ignore[arg-type]
        curve="invalid",  # type: ignore[arg-type]
    )
    payload = modifier.to_dict()
    restored = LayerPerformanceModifier.from_dict(payload)

    assert restored.modifier_id == modifier.modifier_id
    assert restored.name == "Beat swell"
    assert restored.depth == 1.0
    assert restored.polarity == "positive"
    assert restored.curve == "smoothstep"


def test_layer_modifier_applies_beat_pulse_and_restores_baseline() -> None:
    modifier = LayerPerformanceModifier(
        modifier_id="beat-motion",
        name="Beat motion",
        source_id="transport.beat_pulse",
        target_id="generator.animation_amount",
        depth=0.1,
        curve="linear",
        attack_ms=1.0,
        release_ms=1.0,
    )
    layer = Layer(
        id="geometry",
        source_type="generator",
        generator_type="geometry",
        generator_settings={"animation_amount": 12.0},
        performance_modifiers=[modifier.to_dict()],
    )
    store, get_target, set_target = _memory_target_store({
        "geometry": {"generator.animation_amount": 12.0}
    })
    engine = LayerPerformanceModifierEngine()

    outputs = engine.evaluate(
        [layer],
        {"transport.beat_pulse": 1.0},
        get_target,
        set_target,
        now=10.0,
    )

    assert outputs[("geometry", "generator.animation_amount")] == 48.0
    assert store["geometry"]["generator.animation_amount"] == 48.0
    assert engine.live_values("geometry")["beat-motion"] == 1.0

    # When the transport source disappears, release the target to its saved base.
    outputs = engine.evaluate(
        [layer],
        {},
        get_target,
        set_target,
        now=11.0,
    )
    assert outputs == {}
    assert store["geometry"]["generator.animation_amount"] == 12.0
    assert engine.live_values("geometry") == {}


def test_modifiers_are_independent_per_layer_and_add_for_one_target() -> None:
    first = LayerPerformanceModifier(
        modifier_id="first",
        source_id="transport.beat_pulse",
        target_id="layer.scale",
        depth=0.1,
        curve="linear",
        attack_ms=1.0,
    )
    second = LayerPerformanceModifier(
        modifier_id="second",
        source_id="macro.energy",
        target_id="layer.scale",
        depth=0.1,
        curve="linear",
        attack_ms=1.0,
    )
    layers = [
        Layer(id="one", performance_modifiers=[first.to_dict()]),
        Layer(id="two", performance_modifiers=[second.to_dict()]),
    ]
    store, get_target, set_target = _memory_target_store({
        "one": {"layer.scale": 1.0},
        "two": {"layer.scale": 1.0},
    })
    engine = LayerPerformanceModifierEngine()

    outputs = engine.evaluate(
        layers,
        {"transport.beat_pulse": 1.0, "macro.energy": 0.5},
        get_target,
        set_target,
        now=1.0,
    )

    assert outputs[("one", "layer.scale")] == 1.195
    assert outputs[("two", "layer.scale")] == 1.0975
    assert store["one"]["layer.scale"] > store["two"]["layer.scale"]


def test_manual_override_temporarily_yields_layer_modifier_to_user_value() -> None:
    modifier = LayerPerformanceModifier(
        modifier_id="manual-test",
        source_id="transport.downbeat_pulse",
        target_id="layer.opacity",
        depth=0.2,
        curve="linear",
        attack_ms=1.0,
    )
    layer = Layer(
        id="manual-layer",
        opacity=0.5,
        performance_modifiers=[modifier.to_dict()],
    )
    store, get_target, set_target = _memory_target_store({
        "manual-layer": {"layer.opacity": 0.5}
    })
    engine = LayerPerformanceModifierEngine()

    engine.evaluate(
        [layer], {"transport.downbeat_pulse": 1.0},
        get_target, set_target, now=2.0,
    )
    assert store["manual-layer"]["layer.opacity"] == 0.7

    engine.notify_manual_override(
        "manual-layer",
        {"layer.opacity"},
        layer.performance_modifiers,
        duration_seconds=3.0,
        now=3.0,
    )
    store["manual-layer"]["layer.opacity"] = 0.35

    engine.evaluate(
        [layer], {"transport.downbeat_pulse": 1.0},
        get_target, set_target, now=4.0,
    )
    assert store["manual-layer"]["layer.opacity"] == 0.35

    engine.evaluate(
        [layer], {"transport.downbeat_pulse": 1.0},
        get_target, set_target, now=6.1,
    )
    assert store["manual-layer"]["layer.opacity"] == 0.55


def test_modifier_engine_exposes_pre_modulation_values_for_project_save() -> None:
    modifier = LayerPerformanceModifier(
        modifier_id="save-test",
        source_id="transport.phrase_pulse",
        target_id="generator.text_animation_amount",
        depth=0.5,
        curve="linear",
        attack_ms=1.0,
    )
    layer = Layer(
        id="text",
        source_type="generator",
        generator_type="text",
        generator_settings={"text_animation_amount": 0.02},
        performance_modifiers=[modifier.to_dict()],
    )
    _store, get_target, set_target = _memory_target_store({
        "text": {"generator.text_animation_amount": 0.02}
    })
    engine = LayerPerformanceModifierEngine()
    engine.evaluate(
        [layer], {"transport.phrase_pulse": 1.0},
        get_target, set_target, now=5.0,
    )

    assert engine.base_values() == {
        ("text", "generator.text_animation_amount"): 0.02
    }

def test_external_transport_exposes_beat_downbeat_phrase_and_bar_phase(monkeypatch) -> None:
    from types import SimpleNamespace

    from core.application import Application

    application = Application.__new__(Application)
    application._audio_sources = {}
    application.performance_control = SimpleNamespace(
        intensity=0.6,
        source_id="sonic_pi",
        transport_running=True,
        beats_per_bar=4,
        bpm=120.0,
        bar_index=1,
        macros={"energy": 0.7, "cutoff": 0.4},
    )
    application.transport = SimpleNamespace(
        phrase_bars=4,
        running=False,
        paused=False,
    )
    application._external_clock_bar_at = 100.0
    monkeypatch.setattr("core.application.time.monotonic", lambda: 100.025)

    sources = application._modulation_sources()

    assert sources["transport.beat_pulse"] > 0.7
    assert sources["transport.downbeat_pulse"] == sources["transport.beat_pulse"]
    assert sources["transport.phrase_pulse"] == sources["transport.beat_pulse"]
    assert sources["transport.bar_phase"] == 0.0125
    assert sources["macro.energy"] == 0.7
    assert sources["macro.cutoff"] == 0.4

    # Half a second later the sender is on beat two, not on the downbeat.
    monkeypatch.setattr("core.application.time.monotonic", lambda: 100.525)
    sources = application._modulation_sources()
    assert sources["transport.beat_pulse"] > 0.7
    assert sources["transport.downbeat_pulse"] == 0.0
    assert sources["transport.phrase_pulse"] == 0.0


def test_rhythm_sources_are_zero_when_transport_is_stopped(monkeypatch) -> None:
    from types import SimpleNamespace

    from core.application import Application

    application = Application.__new__(Application)
    application._audio_sources = {}
    application.performance_control = SimpleNamespace(
        intensity=0.0,
        source_id="sonic_pi",
        transport_running=False,
        beats_per_bar=4,
        bpm=92.0,
        bar_index=0,
        macros={},
    )
    application.transport = SimpleNamespace(
        phrase_bars=4,
        running=False,
        paused=False,
    )
    application._external_clock_bar_at = None
    monkeypatch.setattr("core.application.time.monotonic", lambda: 100.0)

    sources = application._modulation_sources()

    assert sources["transport.phase"] == 0.0
    assert sources["transport.bar_phase"] == 0.0
    assert sources["transport.beat_pulse"] == 0.0
    assert sources["transport.downbeat_pulse"] == 0.0
    assert sources["transport.phrase_pulse"] == 0.0


def test_application_reads_and_writes_layer_scoped_generator_targets() -> None:
    from core.application import Application
    from core.composition import Composition

    layer = Layer(
        id="app-layer",
        source_type="generator",
        generator_type="text",
        generator_settings={
            "text_animation_amount": 0.025,
            "text_animation_speed": 1.0,
            "font_size": 148,
        },
    )
    application = Application.__new__(Application)
    application.composition = Composition(layers=[layer])
    application._overlay_images = {}

    assert application._get_layer_modifier_target(
        "app-layer", "generator.text_animation_amount"
    ) == 0.025
    assert application._set_layer_modifier_target(
        "app-layer", "generator.text_animation_amount", 0.12
    )
    assert layer.generator_settings["text_animation_amount"] == 0.12

    assert application._set_layer_modifier_target(
        "app-layer", "layer.rotation", 45.0
    )
    assert layer.rotation == 45.0

