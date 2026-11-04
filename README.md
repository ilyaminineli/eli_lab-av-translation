# ELI LAB AV Translation

A Windows-first live audiovisual compositor for video collage, generative visuals, audio-reactive graphics and Sonic Pi control.

The first implementation focuses on a usable video instrument: scan local folders, load footage into four independent decks, composite them on a GPU canvas, randomize the scene and save the composition.

## Current implementation

### M0 — Rendering Core
- PySide6 desktop shell with dockable media, deck and layer panels.
- Qt OpenGL widget and ModernGL context initialization.
- Composition/layer data model and event bus.
- Atomic JSON project persistence using the .eliav extension.
- Renderer diagnostics and continuous preview refresh.

### M1 — Video Collage
- Recursive video folder scanner and metadata probing through PyAV.
- SQLite-backed media index stored in the user's application data folder.
- Background thumbnail generation.
- Four independent, timestamp-paced video decoder workers.
- Bounded frame queues that prefer recent frames.
- GPU texture upload and a ping-pong framebuffer compositor.
- Normal, Add, Screen, Multiply and Difference blend modes.
- Layer transforms, opacity, visibility and z-order.
- Random deck assignment and randomized collage layout with locks.

M2 generators/effects, M3 audio analysis and M4 Sonic Pi OSC integration are planned but are not yet implemented.

## System requirements

- Windows 10/11, 64-bit.
- Python 3.12, 64-bit.
- GPU and current graphics driver supporting OpenGL 3.3 Core Profile.
- Video codecs supported by the FFmpeg build used by PyAV.
- SSD and modern CPU/GPU recommended for four concurrent streams.

See docs/SETUP_WINDOWS.md for detailed setup, troubleshooting and first-run instructions.

## Quick setup (Windows PowerShell)

Clone the repository and switch to the implementation branch:

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation
    git fetch origin
    git checkout implementation/m0-m1-first-test

Create and activate a Python 3.12 virtual environment:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1

Install development dependencies and the project:

    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
    python -m pip install -e . --no-deps

Launch:

    python main.py

For an application-only environment, install requirements.txt instead of requirements-dev.txt.

## First test

Generate sample clips:

    python scripts/generate_test_videos.py --output test-footage

Then launch the app, select File → Add Media Folder, import test-footage, assign clips to the four decks, adjust layers and try RANDOM SET and RANDOMIZE LAYOUT.

Save a project with File → Save Project As. Projects use the .eliav extension.

## Tests and quality checks

    python -m compileall -q .
    python -m pytest tests/unit -v
    python -m ruff check .

Windows GitHub Actions runs compilation and unit tests on pushes and pull requests.

## Project data and media cache

The media index, thumbnails and log file are stored under the user's application data directory, not in the repository. Source videos are never copied into the project.

## Known first-build limitations

- The first build is visual-only; it does not play or mix audio.
- Sonic Pi OSC, MIDI, generators, masks, transitions, recording and external output are future milestones.
- Playback timing is timestamp-based but does not guarantee four arbitrary high-bitrate 1080p streams on every computer.
- The initial compositor stretches footage to the canvas aspect ratio. Aspect-fit/crop controls are planned.
- Projects store absolute footage paths; a media relinking workflow is planned.
