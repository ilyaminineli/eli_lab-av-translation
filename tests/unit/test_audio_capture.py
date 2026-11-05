from __future__ import annotations

import time

import numpy as np

from core.audio_analysis import AudioAnalysisFrame
from core.audio_capture import (
    AudioCaptureService,
    AudioCaptureState,
    AudioFrameQueue,
    AudioInputDevice,
)


class _FakeRecorder:
    def __init__(self, channels: int = 2) -> None:
        self.channels = channels
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.closed = True

    def record(self, numframes: int):
        time.sleep(0.001)
        return np.full((numframes, self.channels), 0.2, dtype=np.float32)


class _FakeBackend:
    def __init__(self) -> None:
        self.devices = [
            AudioInputDevice("mic-1", "Test microphone", 2, False),
            AudioInputDevice("loop-1", "System output", 2, True, "loopback"),
        ]
        self.recorders = []

    def list_devices(self):
        return list(self.devices)

    def open_recorder(self, device_id: str, sample_rate: int, block_size: int):
        recorder = _FakeRecorder()
        self.recorders.append((device_id, recorder))
        return recorder


def _wait_for_frame(service: AudioCaptureService) -> bool:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if service.latest_frame() is not None:
            return True
        time.sleep(0.01)
    return False


def test_audio_capture_uses_owned_worker_for_physical_and_loopback_sources() -> None:
    backend = _FakeBackend()
    service = AudioCaptureService(backend=backend, sample_rate=48000, block_size=256)
    try:
        assert len(service.list_devices()) == 2
        service.start("mic-1")
        assert _wait_for_frame(service)
        assert service.state == AudioCaptureState.RUNNING
        assert service.stop() is True
        assert backend.recorders[-1][1].closed is True

        service.start("loop-1")
        assert _wait_for_frame(service)
        assert service.source_kind == "loopback"
        assert service.stop() is True
    finally:
        service.shutdown()


def test_audio_capture_can_switch_to_deterministic_test_signal() -> None:
    service = AudioCaptureService(sample_rate=48000, block_size=256)
    try:
        service.start_test_signal(120)
        assert _wait_for_frame(service)
        assert service.state == AudioCaptureState.RUNNING
        assert service.selected_device_id == "test-signal"
    finally:
        assert service.stop() is True


def test_audio_capture_detects_removed_device_without_blocking_caller() -> None:
    backend = _FakeBackend()
    service = AudioCaptureService(backend=backend, sample_rate=48000, block_size=256)
    try:
        service.start("mic-1")
        assert _wait_for_frame(service)
        backend.devices = []
        assert service.refresh_device_state() is False
        assert service.state == AudioCaptureState.DEVICE_LOST
        service.stop()
    finally:
        service.shutdown()


def test_audio_capture_replays_recorded_fixture() -> None:
    service = AudioCaptureService(sample_rate=48000, block_size=256)
    fixture = np.sin(
        np.arange(4096, dtype=np.float32) * (2.0 * np.pi * 220.0 / 48000)
    )
    try:
        service.start_replay(fixture, 48000, repeat=False)
        assert _wait_for_frame(service)
        deadline = time.monotonic() + 2.0
        while service.state != AudioCaptureState.STOPPED and time.monotonic() < deadline:
            time.sleep(0.01)
        assert service.state == AudioCaptureState.STOPPED
        assert service.latest_frame() is not None
    finally:
        service.shutdown()


def test_audio_frame_queue_is_bounded_and_keeps_the_latest_values() -> None:
    queue = AudioFrameQueue(capacity=2)
    for index in range(3):
        queue.push_latest(AudioAnalysisFrame(
            timestamp=float(index),
            sample_rate=48000,
            rms=index / 3,
            peak=index / 3,
            low=0,
            mid=0,
            high=0,
            onset=0,
            bpm=None,
            beat_confidence=0,
        ))
    assert queue.dropped == 1
    assert len(queue) == 2
    assert [frame.timestamp for frame in queue.drain(3)] == [1.0, 2.0]
