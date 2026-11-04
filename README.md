# ELI LAB AV Translation

A Windows-first live video collage and VJ performance environment. Drop in a footage folder, choose a session rhythm, start automation and send the same GPU composition to a separate fullscreen display or projector.

This development pass focuses on video, master effects, overlays and automation. Audio analysis, audio playback and Sonic Pi control are intentionally outside this milestone.

## Current implementation

### M0 — Rendering Core
- PySide6 desktop shell with dockable media, deck, layer, effects and automation panels.
- Qt OpenGL widget with ModernGL rendering.
- Composition/layer data model and atomic .eliav project persistence.

### M1 — Video Collage
- Recursive local video indexing and cached thumbnails.
- Four independent PyAV decoder decks.
- Per-deck playback, loop controls, layer transforms and blend modes.
- GPU texture upload and a multi-layer ping-pong framebuffer compositor.

### M2 — Automated Collage, Effects and Projector Output
- Drag-and-drop folder import in the Media Library.
- Random in/out segment selection for every deck.
- Segment looping or one-shot cuts, with independent random cut timers.
- Semi-random collage layouts: grids, split screens, picture-in-picture and stacked compositions.
- A master filter / overlay pass with brightness, contrast, saturation, gamma, vignette, grain, scanlines, RGB split, glitch, pixelation, posterize and invert.
- Built-in looks: Clean, 16mm Film, VHS / Tape, CRT, Bleach Bypass, Dream Haze and Digital Damage.
- Unattended sessions for 30, 45, 60, 90 or 120 minutes, or until manually stopped.
- A separate fullscreen output window selectable by Windows display / projector.
- Shared decoded-frame snapshots so preview and projector outputs show the same playback without competing for frames.
- Effect and automation settings saved inside .eliav projects.

## Development roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the complete M0–M5 plan, implementation status and the Video Mixer Completion Gate. The current priority is to finish and harden M0–M2 before starting audio-reactive and Sonic Pi work.

## System requirements

- Windows 10/11, 64-bit.
- Python 3.12, 64-bit.
- Current GPU driver supporting OpenGL 3.3 Core Profile.
- Video codecs supported by the FFmpeg build bundled with PyAV.
- SSD and modern CPU/GPU recommended for four concurrent streams.

See docs/SETUP_WINDOWS.md for installation and troubleshooting.

## Quick setup (Windows PowerShell)

Clone the current main branch:

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation
    git checkout main
    git pull

Create and activate a Python 3.12 virtual environment:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1

Install development dependencies and the project:

    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
    python -m pip install -e . --no-deps

Launch:

    python main.py

## First unattended session

1. Drag a folder of videos from Windows Explorer into the Media Library, or select File → Add Media Folder.
2. Wait for the folder scan to finish.
3. Open the AUTO PERFORMANCE panel.
4. Choose the footage pool, session length, cut rhythm, segment length and loop probability.
5. Leave layout and filter-look automation enabled.
6. Press START AUTOMATIC SESSION.
7. Open View → PROJECTOR OUTPUT → Display N to send the same live composition to a second display or projector.
8. Press Escape on the projector output to close that output window. Stop automation in the main window when finished.

The deck and layer lock controls are respected by automation. Lock anything that should remain untouched.

## Media library cleanup

Use the **LIBRARY** menu in the Media Library panel to remove a selected imported folder from the index, prune missing source files, clear the entire index, or delete unused cached thumbnails. These operations never delete the original video files. Clips already loaded into decks continue playing when their folder is removed from the index. During Auto Mode, library changes also refresh the eligible source pool without forcing an immediate cut.

## Performance behaviour

Preview decoding is currently capped at 30 output frames per second and 1920×1080 per deck; smaller sources remain at native size. These are preview/output limits only—the original files are not modified. The render status reports FPS, rolling per-second CPU-side decode and conversion costs, renderer CPU submission time, texture upload time and bandwidth, active deck count and dropped frames per second. These measurements help identify the next bottleneck; CPU-side render timing is not the same as a GPU timer query.

## Effects and overlays

The EFFECTS + OVERLAYS panel controls the master output. Presets are starting looks; every parameter can be adjusted manually. Automated look changes use the same presets and affect the preview and projector output together.

## Test footage and tests

Generate synthetic sample clips:

    python scripts/generate_test_videos.py --output test-footage

Run unit tests and lint:

    python -m compileall -q .
    python -m pytest tests/unit -v
    python -m ruff check .

Windows GitHub Actions runs compilation, unit tests and Ruff.

## Project data

The media index, thumbnails and logs are stored under %LOCALAPPDATA%\ELI LAB\AV Translation\. Source videos are never copied into a project. .eliav projects store media paths, composition, deck segment settings, effect settings and automation settings.

## Current limitations

- Effects are master-output GLSL filters, not an unlimited per-layer node graph.
- The first projector implementation uses an independent renderer and CPU frame snapshots; each output uploads textures locally.
- No audio playback, audio-reactive analysis, MIDI or Sonic Pi OSC in this video/automation-focused pass.
- No reverse playback, variable-speed playback, masks, keying, advanced crossfades or recording yet.
- Four simultaneous high-bitrate 1080p/4K clips are not guaranteed on every computer; start with H.264 test clips and check the renderer / CPU load.
- Projects store absolute media paths. Moving source footage requires re-importing the folder.
