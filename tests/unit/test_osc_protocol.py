from __future__ import annotations

import socket
import time

from pythonosc.udp_client import SimpleUDPClient

from core.osc_protocol import OSCProtocolAdapter, OSCReceiver


def test_protocol_decodes_transport_bar_scene_macro_and_cue() -> None:
    adapter = OSCProtocolAdapter()
    start = adapter.decode(
        "/eli_lab/v1/transport/start",
        ("session-a", 1, 92.0, 4),
    )
    assert start.kind == "transport.start"
    assert start.payload == {"bpm": 92.0, "beats_per_bar": 4}
    assert start.sequence == 1

    tempo = adapter.decode(
        "/eli_lab/v1/transport/tempo",
        ("session-a", 2, 92.0),
    )
    assert tempo.kind == "transport.tempo"
    assert tempo.payload == {"bpm": 92.0}

    bar = adapter.decode(
        "/eli_lab/v1/clock/bar",
        ("session-a", 3, 1, 92.0, 4),
    )
    assert bar.kind == "clock.bar"
    assert bar.payload["bar_index"] == 1

    scene = adapter.decode(
        "/eli_lab/v1/scene/select",
        ("session-a", 4, "dev", 0.62, 80),
    )
    assert scene.payload == {"scene_id": "dev", "intensity": 0.62, "bar_index": 80}

    macro = adapter.decode(
        "/eli_lab/v1/macro/set",
        ("session-a", 5, "cutoff", 0.5),
    )
    assert macro.kind == "macro.set"
    assert macro.payload == {"name": "cutoff", "value": 0.5}

    cue = adapter.decode(
        "/eli_lab/v1/cue/trigger",
        ("session-a", 6, "phrase_20"),
    )
    assert cue.payload == {"name": "phrase_20"}


def test_protocol_rejects_unknown_routes_types_ranges_and_macro_names() -> None:
    adapter = OSCProtocolAdapter()
    adapter.decode("/eli_lab/v1/transport/start", ("session-a", 1, 92.0, 4))
    invalid = (
        ("/eli_lab/v1/unknown", ("session-a", 2)),
        ("/eli_lab/v1/macro/set", ("session-a", 2, "volume", 0.5)),
        ("/eli_lab/v1/macro/set", ("session-a", 2, "energy", 1.1)),
        ("/eli_lab/v1/clock/bar", ("session-a", 2, 0, 92.0, 4)),
        ("/eli_lab/v1/scene/select", ("session-a", 2, "dev", True, 2)),
        ("/eli_lab/v1/scene/select", ("session-a", 2, "unknown", 0.5, 2)),
        ("/eli_lab/v1/transport/tempo", ("session-a", 2, float("nan"))),
    )
    for address, args in invalid:
        try:
            adapter.decode(address, args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected {address} {args!r} to be rejected.")


def test_protocol_deduplicates_sequences_and_requires_new_restart_session() -> None:
    adapter = OSCProtocolAdapter()
    adapter.decode("/eli_lab/v1/transport/start", ("session-a", 1, 92.0, 4))
    try:
        adapter.decode("/eli_lab/v1/clock/bar", ("session-a", 1, 1, 92.0, 4))
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("Duplicate sequence was accepted.")

    adapter.decode("/eli_lab/v1/transport/start", ("session-b", 1, 100.0, 4))
    try:
        adapter.decode("/eli_lab/v1/clock/bar", ("session-a", 2, 2, 92.0, 4))
    except ValueError as exc:
        assert "active session" in str(exc)
    else:
        raise AssertionError("A packet from an old session was accepted.")

    try:
        adapter.decode("/eli_lab/v1/transport/start", ("session-b", 2, 100.0, 4))
    except ValueError as exc:
        assert "reused" in str(exc)
    else:
        raise AssertionError("A session ID was reused.")


def test_protocol_recovers_after_a_lost_sequence_number() -> None:
    adapter = OSCProtocolAdapter()
    adapter.decode(
        "/eli_lab/v1/transport/start",
        ("session-gap", 1, 92.0, 4),
    )

    # Sequence 2 represents a UDP datagram that never arrived.
    bar = adapter.decode(
        "/eli_lab/v1/clock/bar",
        ("session-gap", 3, 1, 92.0, 4),
    )
    assert bar.sequence == 3
    assert bar.payload["bar_index"] == 1

    macro = adapter.decode(
        "/eli_lab/v1/macro/set",
        ("session-gap", 4, "energy", 0.68),
    )
    assert macro.payload == {"name": "energy", "value": 0.68}


def test_receiver_accepts_local_udp_without_touching_application_state() -> None:
    received = []
    receiver = OSCReceiver(lambda event: received.append(event) or True)
    port = receiver.start("127.0.0.1", 0)
    client = SimpleUDPClient("127.0.0.1", port)
    try:
        client.send_message(
            "/eli_lab/v1/transport/start",
            ["udp-test", 1, 92.0, 4],
        )
        deadline = time.monotonic() + 2.0
        while not received and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(received) == 1
        assert received[0].kind == "transport.start"
        assert received[0].source == "sonic_pi"
        assert receiver.snapshot()["accepted"] == 1
    finally:
        receiver.stop()


def test_local_test_sender_streams_a_complete_session_over_udp() -> None:
    import subprocess
    import sys
    from pathlib import Path

    received = []
    receiver = OSCReceiver(lambda event: received.append(event) or True)
    port = receiver.start("127.0.0.1", 0)
    repo_root = Path(__file__).resolve().parents[2]
    sender = repo_root / "scripts" / "osc_test_sender.py"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(sender),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        assert "Sent 15 /eli_lab/v1 messages" in result.stdout

        deadline = time.monotonic() + 2.0
        while len(received) < 15 and time.monotonic() < deadline:
            time.sleep(0.01)

        assert len(received) == 15
        assert received[0].kind == "transport.start"
        assert received[1].kind == "transport.tempo"
        assert received[-2].kind == "cue.trigger"
        assert received[-2].payload == {"name": "end"}
        assert received[-1].kind == "transport.stop"
        assert [event.sequence for event in received] == list(range(1, 16))
        assert len({event.session_id for event in received}) == 1
        assert receiver.snapshot()["accepted"] == 15
    finally:
        receiver.stop()


def test_receiver_recovers_after_invalid_datagram_and_counts_queue_drops() -> None:
    receiver = OSCReceiver(lambda _event: False)
    port = receiver.start("127.0.0.1", 0)
    client = SimpleUDPClient("127.0.0.1", port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(b"not-an-osc-packet", ("127.0.0.1", port))
        client.send_message(
            "/eli_lab/v1/transport/start",
            ["udp-drop", 1, 92.0, 4],
        )
        deadline = time.monotonic() + 2.0
        while receiver.snapshot()["received"] < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        while receiver.snapshot()["dropped"] < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        snapshot = receiver.snapshot()
        assert snapshot["running"] is True
        assert snapshot["dropped"] == 1
        assert snapshot["rejected"] >= 1
    finally:
        sock.close()
        receiver.stop()


def test_sonic_pi_start_takes_authority_from_internal_test_clock() -> None:
    from core.application import Application
    from core.event_bus import EventBus
    from core.performance_control import (
        ControlEvent,
        ControlEventQueue,
        PerformanceControlState,
    )
    from core.performance_transport import InternalTransport

    application = Application.__new__(Application)
    application.events = EventBus()
    application.control_events = ControlEventQueue()
    application.performance_control = PerformanceControlState()
    application.transport = InternalTransport()
    application.transport.start()

    assert application.transport.running is True
    assert application.submit_control_event(ControlEvent(
        "transport.start",
        "sonic_pi",
        {"bpm": 92.0, "beats_per_bar": 4},
        sequence=1,
        session_id="session-sonata",
    ))

    assert application.process_control_events() == 1
    assert application.transport.running is False
    assert application.performance_control.transport_running is True
    assert application.performance_control.bpm == 92.0
    assert application.performance_control.beats_per_bar == 4


def test_sonic_pi_clock_drives_m3_transport_phase_modulation_source() -> None:
    from core.application import Application
    from core.performance_control import PerformanceControlState
    from core.performance_transport import InternalTransport

    application = Application.__new__(Application)
    application.performance_control = PerformanceControlState(bpm=120.0)
    application.performance_control.source_id = "sonic_pi"
    application.performance_control.transport_running = True
    application.transport = InternalTransport()
    application._audio_sources = {}
    application._external_clock_bar_at = time.monotonic() - 0.25

    sources = application._modulation_sources()
    assert 0.35 <= sources["transport.phase"] <= 0.65


def test_receiver_rate_limits_all_udp_datagrams() -> None:
    received = []
    receiver = OSCReceiver(
        lambda event: received.append(event) or True,
        max_messages_per_second=1,
    )
    port = receiver.start("127.0.0.1", 0)
    client = SimpleUDPClient("127.0.0.1", port)
    try:
        client.send_message(
            "/eli_lab/v1/transport/start",
            ["rate-test", 1, 92.0, 4],
        )
        client.send_message(
            "/eli_lab/v1/source/heartbeat",
            ["rate-test", 2],
        )
        deadline = time.monotonic() + 2.0
        while receiver.snapshot()["rate_limited"] < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        snapshot = receiver.snapshot()
        assert snapshot["rate_limited"] >= 1
        assert snapshot["accepted"] == 1
        assert len(received) == 1
    finally:
        receiver.stop()


def test_sonic_pi_macro_events_feed_existing_m3_modulation_sources() -> None:
    from core.application import Application
    from core.performance_control import PerformanceControlState
    from core.performance_transport import InternalTransport

    adapter = OSCProtocolAdapter()
    start = adapter.decode("/eli_lab/v1/transport/start", ("macro-session", 1, 92.0, 4))
    energy = adapter.decode(
        "/eli_lab/v1/macro/set",
        ("macro-session", 2, "energy", 0.74),
    )
    cutoff = adapter.decode(
        "/eli_lab/v1/macro/set",
        ("macro-session", 3, "cutoff", 0.38),
    )
    state = PerformanceControlState()
    assert state.apply(start)
    assert state.apply(energy)
    assert state.apply(cutoff)

    application = Application.__new__(Application)
    application.performance_control = state
    application.transport = InternalTransport()
    application._audio_sources = {}
    application._external_clock_bar_at = None
    sources = application._modulation_sources()
    assert sources["macro.energy"] == 0.74
    assert sources["macro.cutoff"] == 0.38

def test_sonic_pi_bar_takes_clock_authority_when_start_packet_was_lost() -> None:
    from core.application import Application
    from core.event_bus import EventBus
    from core.performance_control import ControlEvent, ControlEventQueue, PerformanceControlState
    from core.performance_transport import InternalTransport

    application = Application.__new__(Application)
    application.events = EventBus()
    application.control_events = ControlEventQueue()
    application.performance_control = PerformanceControlState()
    application.transport = InternalTransport(bpm=120.0, beats_per_bar=4)
    application.transport.start()
    application._external_clock_bar_at = None

    # The transport/start datagram is assumed lost; the first accepted packet is bar 1.
    assert application.submit_control_event(ControlEvent(
        "clock.bar",
        "sonic_pi",
        {"bar_index": 1, "bpm": 92.0, "beats_per_bar": 4},
        sequence=2,
        session_id="lost-start-session",
    ))

    assert application.process_control_events() == 1
    assert application.transport.running is False
    assert application.performance_control.transport_running is True
    assert application.performance_control.source_id == "sonic_pi"
    assert application.performance_control.bpm == 92.0
    assert application.performance_control.bar_index == 1
    assert application._external_clock_bar_at is not None

