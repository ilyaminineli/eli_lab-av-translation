from __future__ import annotations

import pytest

from core.performance_control import (
    ControlEvent,
    ControlEventQueue,
    PerformanceControlState,
)


def test_control_event_validates_protocol_fields() -> None:
    event = ControlEvent(
        "scene.select",
        "sonicpi",
        {"scene_id": "rc_w", "intensity": 1.0},
        sequence=12,
        session_id="sonata-01",
    )
    assert event.source == "sonicpi"
    assert event.sequence == 12
    assert event.payload["scene_id"] == "rc_w"

    with pytest.raises(ValueError):
        ControlEvent("python.exec", "sonicpi")

    with pytest.raises(ValueError):
        ControlEvent("scene.select", "sonicpi", {"bad/key": "value"})


def test_control_queue_is_bounded_and_drains_in_order() -> None:
    queue = ControlEventQueue(capacity=2)
    events = [
        ControlEvent("clock.bar", "test", {"bar_index": 1}),
        ControlEvent("clock.bar", "test", {"bar_index": 2}),
        ControlEvent("clock.bar", "test", {"bar_index": 3}),
    ]

    assert queue.submit(events[0]) is True
    assert queue.submit(events[1]) is True
    assert queue.submit(events[2]) is False
    assert len(queue) == 2
    assert queue.dropped_events == 1
    assert queue.drain(1) == [events[0]]
    assert queue.drain(10) == [events[1]]
    assert len(queue) == 0


def test_performance_control_state_applies_transport_scene_and_macros() -> None:
    state = PerformanceControlState()

    assert state.apply(ControlEvent(
        "transport.start",
        "sonicpi",
        {"bpm": 92, "beats_per_bar": 4},
        sequence=1,
        session_id="sonata",
    ))
    assert state.apply(ControlEvent(
        "clock.bar",
        "sonicpi",
        {"bar_index": 200, "bpm": 92},
        sequence=2,
        session_id="sonata",
    ))
    assert state.apply(ControlEvent(
        "scene.select",
        "sonicpi",
        {"scene_id": "rc_w", "intensity": 1.0, "bar_index": 200},
        sequence=3,
        session_id="sonata",
    ))
    assert state.apply(ControlEvent(
        "macro.set",
        "sonicpi",
        {"name": "energy", "value": 0.87},
        sequence=4,
        session_id="sonata",
    ))
    assert state.apply(ControlEvent(
        "cue.trigger",
        "sonicpi",
        {"name": "phrase"},
        sequence=5,
        session_id="sonata",
    ))

    snapshot = state.snapshot()
    assert snapshot["transport_running"] is True
    assert snapshot["bpm"] == 92.0
    assert snapshot["bar_index"] == 200
    assert snapshot["scene_id"] == "rc_w"
    assert snapshot["intensity"] == 1.0
    assert snapshot["macros"] == {"energy": 0.87}
    assert snapshot["last_cue"] == "phrase"
    assert "RC_W" in state.status_text()


def test_performance_control_state_clamps_only_by_rejecting_unsafe_values() -> None:
    state = PerformanceControlState()

    with pytest.raises(ValueError):
        state.apply(ControlEvent(
            "transport.tempo", "test", {"bpm": 600}
        ))
    with pytest.raises(ValueError):
        state.apply(ControlEvent(
            "scene.intensity", "test", {"intensity": 1.2}
        ))
    with pytest.raises(ValueError):
        state.apply(ControlEvent(
            "macro.set", "test", {"name": "energy", "value": -0.1}
        ))


def test_performance_control_state_ignores_duplicate_sequences_per_session() -> None:
    state = PerformanceControlState()
    first = ControlEvent(
        "scene.select",
        "sonicpi",
        {"scene_id": "dev", "intensity": 0.62},
        sequence=10,
        session_id="session-a",
    )
    duplicate = ControlEvent(
        "scene.select",
        "sonicpi",
        {"scene_id": "peak", "intensity": 1.0},
        sequence=10,
        session_id="session-a",
    )
    next_session = ControlEvent(
        "scene.select",
        "sonicpi",
        {"scene_id": "peak", "intensity": 1.0},
        sequence=1,
        session_id="session-b",
    )

    assert state.apply(first) is True
    assert state.apply(duplicate) is False
    assert state.scene_id == "dev"
    assert state.apply(next_session) is True
    assert state.scene_id == "peak"


def test_transport_stop_and_reset_restore_safe_idle_state() -> None:
    state = PerformanceControlState()
    state.apply(ControlEvent("transport.start", "test", {"bpm": 128}))
    state.apply(ControlEvent("scene.select", "test", {"scene_id": "peak", "intensity": 1.0}))
    state.apply(ControlEvent("transport.stop", "test"))

    assert state.transport_running is False
    assert state.scene_id == "peak"

    state.reset()
    assert state.transport_running is False
    assert state.scene_id == "idle"
    assert state.intensity == 0.0
    assert state.macros == {}


def test_invalid_event_does_not_partially_change_state_or_consume_sequence() -> None:
    state = PerformanceControlState()
    invalid_start = ControlEvent(
        "transport.start",
        "sonicpi",
        {"bpm": 92, "beats_per_bar": 24},
        sequence=100,
        session_id="sonata",
    )

    with pytest.raises(ValueError):
        state.apply(invalid_start)

    assert state.bpm == 120.0
    assert state.beats_per_bar == 4
    assert state.transport_running is False

    valid_start = ControlEvent(
        "transport.start",
        "sonicpi",
        {"bpm": 92, "beats_per_bar": 4},
        sequence=99,
        session_id="sonata",
    )
    assert state.apply(valid_start) is True
    assert state.bpm == 92.0
    assert state.transport_running is True


def test_scene_event_rejects_invalid_scene_identifier() -> None:
    state = PerformanceControlState()
    event = ControlEvent(
        "scene.select",
        "sonicpi",
        {"scene_id": "../bad", "intensity": 0.5},
    )
    with pytest.raises(ValueError):
        state.apply(event)


def test_transport_meter_event_updates_meter_without_starting_transport() -> None:
    state = PerformanceControlState()
    assert state.apply(ControlEvent(
        "transport.meter",
        "internal",
        {"beats_per_bar": 7},
    ))
    assert state.beats_per_bar == 7
    assert state.transport_running is False
    assert state.transport_paused is False
