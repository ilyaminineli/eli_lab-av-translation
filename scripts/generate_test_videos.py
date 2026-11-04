from __future__ import annotations

import argparse
from pathlib import Path

import av
import numpy as np


def create_clip(path: Path, color: tuple[int, int, int], label_phase: int) -> None:
    output = av.open(str(path), mode="w")
    stream = output.add_stream("mpeg4", rate=30)
    stream.width = 640
    stream.height = 360
    stream.pix_fmt = "yuv420p"

    x = np.linspace(0, 1, 640, dtype=np.float32)[None, :, None]
    y = np.linspace(0, 1, 360, dtype=np.float32)[:, None, None]
    base = np.array(color, dtype=np.float32)[None, None, :]
    for index in range(120):
        pulse = 0.5 + 0.5 * np.sin((index / 120.0) * np.pi * 4 + label_phase)
        image = np.clip(base * (0.45 + pulse * 0.45) + x * 35 + y * 20, 0, 255)
        image = np.broadcast_to(image, (360, 640, 3)).astype(np.uint8).copy()
        frame = av.VideoFrame.from_ndarray(image, format="rgb24")
        for packet in stream.encode(frame):
            output.mux(packet)
    for packet in stream.encode():
        output.mux(packet)
    output.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create four short test videos.")
    parser.add_argument("--output", type=Path, default=Path("test-footage"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    samples = [
        ("test-red.mp4", (210, 55, 65), 0),
        ("test-green.mp4", (55, 185, 120), 1),
        ("test-blue.mp4", (65, 110, 220), 2),
        ("test-yellow.mp4", (220, 180, 55), 3),
    ]
    for filename, color, phase in samples:
        destination = args.output / filename
        create_clip(destination, color, phase)
        print(f"Created {destination}")


if __name__ == "__main__":
    main()
