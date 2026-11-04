from __future__ import annotations

from media.video_deck import VideoDeck


class _FakeDecoder:
    instances: list["_FakeDecoder"] = []

    def __init__(self, path, frame_queue, **_kwargs) -> None:
        self.path = path
        self.frame_queue = frame_queue
        self.alive = False
        self.running = False
        self.stop_timeouts: list[float] = []
        self.instances.append(self)

    @property
    def is_running(self) -> bool:
        return self.running

    @property
    def is_playing(self) -> bool:
        return self.running

    @property
    def worker_alive(self) -> bool:
        return self.alive

    @property
    def last_error(self) -> None:
        return None

    @property
    def decoded_frames(self) -> int:
        return 0

    @property
    def published_frames(self) -> int:
        return 0

    @property
    def skipped_output_frames(self) -> int:
        return 0

    def start(self, autoplay: bool = True) -> None:
        self.alive = True
        self.running = autoplay

    def stop(self, timeout: float = 1.0) -> bool:
        self.stop_timeouts.append(timeout)
        self.running = False
        if timeout > 0.2:
            self.alive = False
        return not self.alive

    def play(self) -> None:
        self.running = True

    def pause(self) -> None:
        self.running = False

    def seek(self, _seconds: float) -> None:
        return None

    def set_loop(self, _enabled: bool) -> None:
        return None


def test_replacing_deck_uses_isolated_queue_and_retires_old_decoder(
    tmp_path,
    monkeypatch,
) -> None:
    from media import video_deck

    _FakeDecoder.instances = []
    monkeypatch.setattr(video_deck, "VideoDecoder", _FakeDecoder)
    first_path = tmp_path / "first.mp4"
    second_path = tmp_path / "second.mp4"
    first_path.write_bytes(b"first")
    second_path.write_bytes(b"second")

    deck = VideoDeck("deck_a")
    deck.load(first_path)
    old_decoder = deck.decoder
    old_queue = deck.frame_queue

    deck.load(second_path)

    assert deck.decoder is not old_decoder
    assert deck.frame_queue is not old_queue
    assert deck.decoder.frame_queue is deck.frame_queue
    assert old_decoder.frame_queue is old_queue
    assert old_decoder in deck._retired_decoders
    assert old_decoder.stop_timeouts == [0.2]

    deck.close()

    assert not old_decoder.worker_alive
    assert deck._retired_decoders == []
