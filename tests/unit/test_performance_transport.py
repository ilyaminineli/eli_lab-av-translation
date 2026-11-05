from __future__ import annotations

from core.performance_transport import InternalTransport


def test_internal_transport_emits_one_based_bar_and_zero_based_beat_positions() -> None:
    clock = InternalTransport(bpm=120.0, beats_per_bar=4)
    started = clock.start(now=10.0)
    assert started[0].kind == "transport.start"

    events = clock.tick(now=10.0)
    assert [(event.kind, event.payload.get("bar_index"), event.payload.get("beat_index"))
            for event in events] == [
        ("clock.bar", 1, None),
        ("clock.beat", 1, 0),
    ]

    events = clock.tick(now=10.5)
    assert events[-1].payload["beat_index"] == 1
    assert events[-1].payload["bar_index"] == 1

    events = clock.tick(now=12.0)
    assert any(
        event.kind == "clock.bar" and event.payload["bar_index"] == 2
        for event in events
    )


def test_internal_transport_deadlines_do_not_accumulate_timer_drift() -> None:
    clock = InternalTransport(bpm=120.0)
    clock.start(now=50.0)
    clock.tick(now=50.0)
    first_deadline = clock.next_beat_at
    clock.tick(now=50.5)
    assert clock.next_beat_at == first_deadline + 0.5
    clock.tick(now=51.0)
    assert clock.next_beat_at == first_deadline + 1.0


def test_internal_transport_pause_resume_and_stop() -> None:
    clock = InternalTransport(bpm=100.0)
    clock.start(now=1.0)
    clock.tick(now=1.0)
    assert clock.pause(now=1.1)[0].kind == "transport.pause"
    paused_deadline = clock.next_beat_at
    assert clock.tick(now=10.0) == []
    assert clock.next_beat_at == paused_deadline

    resumed = clock.resume(now=10.0)
    assert resumed[0].kind == "transport.start"
    assert clock.next_beat_at == 10.0 + 0.6
    assert clock.stop(now=11.0)[0].kind == "transport.stop"
    assert clock.running is False


def test_scene_change_can_be_quantized_to_next_bar_and_phrase() -> None:
    clock = InternalTransport(bpm=120.0, beats_per_bar=4, phrase_bars=4)
    clock.start(now=0.0)
    clock.tick(now=0.0)

    clock.schedule_scene("dev", 0.62, "bar", now=0.1)
    events = clock.tick(now=2.0)
    scene = next(event for event in events if event.kind == "scene.select")
    assert scene.payload["scene_id"] == "dev"
    assert scene.payload["bar_index"] == 2

    clock.schedule_scene("peak", 1.0, "phrase", now=1.6)
    clock.tick(now=6.0)
    events = clock.tick(now=8.0)
    scene = next(event for event in events if event.kind == "scene.select")
    assert scene.payload["scene_id"] == "peak"
    assert scene.payload["bar_index"] == 5


def test_tempo_and_meter_are_range_checked() -> None:
    clock = InternalTransport()
    try:
        clock.set_tempo(500)
    except ValueError:
        pass
    else:
        raise AssertionError("Out-of-range tempo was accepted")

    try:
        clock.set_meter(0)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid meter was accepted")



def test_performance_control_state_distinguishes_pause_from_stop() -> None:
    from core.performance_control import ControlEvent, PerformanceControlState

    state = PerformanceControlState()
    state.apply(ControlEvent("transport.start", "test", {"bpm": 120}))
    state.apply(ControlEvent("transport.pause", "test"))
    assert state.transport_running is False
    assert state.transport_paused is True
    assert "PAUSE" in state.status_text()

    state.apply(ControlEvent("transport.stop", "test"))
    assert state.transport_running is False
    assert state.transport_paused is False
    assert "STOP" in state.status_text()
