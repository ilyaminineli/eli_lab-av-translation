from __future__ import annotations

from core.application import Application
from core.event_bus import EventBus
from core.performance_control import ControlEvent, ControlEventQueue, PerformanceControlState


def test_application_drains_control_queue_and_publishes_one_snapshot() -> None:
    application = Application.__new__(Application)
    application.events = EventBus()
    application.control_events = ControlEventQueue()
    application.performance_control = PerformanceControlState()
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
