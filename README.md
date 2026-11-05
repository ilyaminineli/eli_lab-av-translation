# ELI LAB AV Translation

A Windows-first live video collage and VJ performance environment. Drop in a footage folder, choose a session rhythm, start automation and send the same GPU composition to a separate fullscreen display or projector.

M0–M2 establish the visual instrument. M3 software implementation is complete: internal transport, optional audio capture/analysis and a visual modulation matrix. M4 will add Sonic Pi as a timed OSC control source. Audio playback remains the responsibility of Sonic Pi or another external audio application.

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
- A GPU master-effect pass with brightness, exposure, contrast, saturation, gamma, temperature, tint, hue shift, vignette, grain, scanlines, RGB split, glitch, pixelation, posterize, invert, halftone and solarization.
- Master-effect bypass and a clean/effected mix control for live A/B comparison.
- Built-in looks: Clean, 16mm Film, VHS / Tape, CRT, Bleach Bypass, Dream Haze, Digital Damage, Halftone Print, Photocopy, Infrared, Cold Steel and Solarized.
- Unattended sessions for 30, 45, 60, 90 or 120 minutes, or until manually stopped.
- A separate fullscreen output window selectable by Windows display / projector.
- Shared decoded-frame snapshots so preview and projector outputs show the same playback without competing for frames.
- Effect and automation settings saved inside .eliav projects.
- First-class transparent generator layers: procedural geometry, typographic art and waveform graphics.
- Expanded geometry patterns: spiral, moiré and hex-grid; waveform patterns: radial and rose curves.
- Text Art alternate line colours with backward-compatible accent-colour defaults.
- GPU-side pulse, rotation, drift and flicker animation for generator layers.
- Generator content, font choices, transforms, colour, outline and animation settings saved inside .eliav projects.

## Development roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the M0–M5 plan, implementation status and the Video Mixer Completion Gate. The visual release gate remains open while M3 control/audio foundations proceed.

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

## M2 generators and text art

Open View → GENERATORS + TEXT ART to add a transparent Geometry, Text Art, Waveform or Particle layer. Generator layers appear in the normal LAYERS panel and can be positioned, scaled, rotated, blended, hidden and saved like footage layers.

- **Geometry:** rings, grids, radial constructions, crosshatch, nested polygons, spirals, moiré and hex grids.
- **Text Art:** editable multiline text, typographic collage, bilingual random pools, type-on, word/column reveal, line wave, jitter, crawl and signal glitch.
- **Waveform:** layered sine traces, Lissajous figures, orbits, radial traces and rose curves.
- **Particles:** a GPU-generated procedural field with drift, rise, fall or orbit motion and trails.
- **Animation:** pulse, rotate, drift and flicker. Static art is rasterized only when content settings change; animation is handled in the GPU compositing shader.

Generators and media overlays are independent composition layers, so they can appear above or below video and render in both preview and projector output. Animated image playback depends on the image formats enabled by the installed Qt image plugins.

See [docs/M2_GENERATIVE_VISUALS.md](docs/M2_GENERATIVE_VISUALS.md) for details.

## M3 audio-reactive engine and performance control

Open the **AUDIO / CONTROL** dock for the internal BPM/meter clock, start/pause/resume/stop transport, quantized scene selection, scene-look and Japanese palette profiles, physical input/system-loopback selection, deterministic test signal, recorded fixture replay, audio meters and tempo confidence.

The SoundCard capture worker publishes bounded analysis frames for RMS/peak, low/mid/high bands, onset and optional tempo estimation. The modulation matrix maps registered audio/transport/macro sources to registered master-effect, selected-layer, generator and Auto Performance targets. Each route has editable ranges, curve, inversion, smoothing, attack/release, hold, intensity ceiling and bypass. Layer locks and manual overrides take precedence.

M3 persists transport configuration, analysis settings, modulation routes and scene profiles inside .eliav projects; it does not persist active device handles or live audio buffers. The software implementation is complete, with physical Windows input/loopback and reconnect testing remaining as hardware sign-off. See [M3 Audio-Reactive Foundation](docs/M3_AUDIO_REACTIVE_FOUNDATION.md).

## M4 Sonic Pi integration

The SONATA Expanded patch has been inspected as the first target. It uses a 92 BPM bar clock, 16 scenes, and energy/cutoff macros, but currently has no OSC sender. M4 will add a versioned OSC bridge at those high-level musical control points. See [SONATA integration notes](docs/SONIC_PI_SONATA_INTEGRATION.md).

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

- Per-layer effects currently provide a compact shader stack, not an unlimited node graph.
- The first projector implementation uses an independent renderer and CPU frame snapshots; each output uploads textures locally.
- Audio-reactive analysis and visual modulation are implemented; audio playback remains external. Sonic Pi OSC and MIDI are not implemented yet.
- No reverse playback, variable-speed playback, masks, keying, advanced crossfades or recording yet.
- Four simultaneous high-bitrate 1080p/4K clips are not guaranteed on every computer; start with H.264 test clips and check the renderer / CPU load.
- Projects store absolute media paths. Moving source footage requires re-importing the folder.
