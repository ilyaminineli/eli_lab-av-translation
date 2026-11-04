from __future__ import annotations

from pathlib import Path

from media.frame_queue import FrameQueue, VideoFrameData
from media.video_decoder import VideoDecoder


class VideoDeck:
    def __init__(self, deck_id: str) -> None:
        self.id = deck_id
        self.frame_queue = FrameQueue(max_size=3)
        self.decoder: VideoDecoder | None = None
        self.current_frame: VideoFrameData | None = None
        self.path: str | None = None
        self.asset_id: str | None = None
        self.collection_id: str | None = None
        self.loop = True
        self.locked = False

    @property
    def is_playing(self) -> bool:
        return bool(self.decoder and self.decoder.is_playing)

    @property
    def error(self) -> str | None:
        return self.decoder.last_error if self.decoder else None

    def load(
        self,
        path: str | Path,
        asset_id: str | None = None,
        collection_id: str | None = None,
    ) -> None:
        self.close()
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        self.path = str(source)
        self.asset_id = asset_id
        self.collection_id = collection_id
        self.current_frame = None
        self.decoder = VideoDecoder(source, self.frame_queue, loop=self.loop)
        self.decoder.start(autoplay=True)

    def play(self) -> None:
        if not self.path:
            return
        if self.decoder is None or not self.decoder.is_running:
            self.load(self.path, self.asset_id, self.collection_id)
        else:
            self.decoder.play()

    def pause(self) -> None:
        if self.decoder:
            self.decoder.pause()

    def stop(self) -> None:
        if self.decoder:
            self.decoder.stop()
            self.decoder = None
        self.frame_queue.clear()
        self.current_frame = None

    def seek(self, seconds: float) -> None:
        if self.decoder:
            self.decoder.seek(seconds)

    def set_loop(self, enabled: bool) -> None:
        self.loop = bool(enabled)
        if self.decoder:
            self.decoder.set_loop(enabled)

    def consume_latest_frame(self) -> VideoFrameData | None:
        latest = self.frame_queue.pop_latest()
        if latest is not None:
            self.current_frame = latest
        return latest

    def close(self) -> None:
        self.stop()
        self.path = None
        self.asset_id = None
        self.collection_id = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "path": self.path,
            "asset_id": self.asset_id,
            "collection_id": self.collection_id,
            "loop": self.loop,
            "playing": self.is_playing,
            "locked": self.locked,
        }
