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

## Requirements

- Windows 10/11
- Python 3.12 x64
- A GPU/driver supporting OpenGL 3.3 Core
- Video codecs supported by the bundled FFmpeg build used by PyAV

## Setup

Open PowerShell in the repository directory:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    python main.py

If PowerShell blocks activation, run the environment's Python directly:

    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    .\.venv\Scripts\python.exe main.py

## First test

1. Select File → Add Media Folder.
2. Choose a directory containing local video clips.
3. Wait for scanning and thumbnail generation.
4. Select a target deck in the Media Library panel.
5. Double-click a clip to load it into that deck.
6. Repeat with up to four clips.
7. Adjust visibility, opacity and blend mode in the Layers panel.
8. Use Random Set or Randomize Layout.
9. Save a project as .eliav.

## Tests

    python -m compileall -q .
    python -m pytest tests/unit -v

A Windows GitHub Actions workflow runs the same compile and unit-test checks on pushes and pull requests.

## Project data and media cache

The media index, thumbnails and log file are stored under the user's application data directory, not in the repository. Source videos are never copied into the project.

## Known first-build limitations

- The first build is visual-only; it does not play or mix audio.
- Sonic Pi OSC, MIDI, generators, masks, transitions, recording and external output are future milestones.
- Playback timing is timestamp-based but does not guarantee four arbitrary high-bitrate 1080p streams on every computer.
- The initial compositor stretches footage to the canvas aspect ratio. Aspect-fit/crop controls are planned.
- Projects store absolute footage paths; a media relinking workflow is planned.
