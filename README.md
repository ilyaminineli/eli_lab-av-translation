# eli_lab AV Translator

A Windows-first audiovisual performance environment for four-deck video collage, procedural visuals, text art, audio reactivity and Sonic Pi-controlled live shows. Build a single Windows x64 executable for a second performance computer and send the same composition to an HDMI projector.

M0–M2 establish the visual instrument. M3 provides internal transport, optional audio capture/analysis and a visual modulation matrix. M4 adds Sonic Pi as a versioned, timed OSC control source. M5 adds a one-button autonomous show workflow: arm Performance Mode, run SONATA in Sonic Pi, and let musical cues, macros, audio reactivity, modulation curves and AUTO PERFORMANCE run together. Audio playback remains the responsibility of Sonic Pi or another external audio application.

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
- First-class transparent generator layers: procedural geometry, typographic art, waveform graphics and GPU particle fields.
- Expanded geometry patterns: spiral, moiré and hex-grid; waveform patterns: radial and rose curves.
- Text Art alternate line colours with backward-compatible accent-colour defaults.
- GPU-side pulse, rotation, drift and flicker animation for generator layers.
- Imported image, animated image and video overlays with independent playback controls.
- Generator content, font choices, transforms, colour, outline and animation settings saved inside .eliav projects.

## Development roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for milestone status and the independent Video Mixer Completion Gate. See [M5 Autonomous Performance](docs/M5_AUTONOMOUS_PERFORMANCE.md) for the one-button Sonic Pi workflow and [Windows one-file build guide](docs/BUILD_WINDOWS.md) for packaging.

## System requirements

- Windows 11, 64-bit for the packaged performance build.
- OpenGL 3.3 Core Profile and a current graphics driver.
- 16 GB RAM minimum for lighter shows; 32 GB recommended for multi-deck work on an integrated GPU.
- NVMe SSD and H.264 720p/1080p media recommended for the first show test.
- HDMI or supported USB-C DisplayPort output for the projector.
- Sonic Pi installed separately for SONATA OSC integration.

The target computer does not need Python, FFmpeg or Visual Studio when using the packaged EXE. The native one-file build requires a Windows x64 build machine with CPython 3.12 and Visual Studio C++ Build Tools. Hardware capability varies by exact laptop SKU; four simultaneous high-bitrate 4K streams are not guaranteed on integrated graphics.

See [Windows build and deployment](docs/BUILD_WINDOWS.md) and [Windows setup](docs/SETUP_WINDOWS.md).

## Windows one-file executable

The release-readiness branch includes a reproducible one-file build. From a Windows x64 build machine with CPython 3.12 and Visual Studio Build Tools 2022 (Desktop development with C++):

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation
    git checkout release/windows-onefile-readiness
    powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1

The script installs the pinned build profile, checks imports/resources, compiles and lints the Python modules, then uses PySide6 deployment/Nuitka to create one EXE under dist. Copy that EXE to the Lenovo; Python and build tools are not required on the target. Sonic Pi and your video media remain separate.

The GitHub Actions workflow can also build a Windows x64 EXE manually or on a v* tag. See [BUILD_WINDOWS.md](docs/BUILD_WINDOWS.md) for exact prerequisites, deployment details and target-machine checks.

## One-button autonomous performance

1. Prepare the composition: import footage, add geometry/text/waveform/particle generators, and place any animated overlays.
2. In **AUDIO / CONTROL**, choose **System loopback** for FFT-style reactivity to the sound playing on this computer. The selector prefers an available loopback device. Choose **Sonic Pi macros only** when you want SONATA energy/cutoff controls without local audio capture.
3. In **AUTO PERFORMANCE**, choose Generative or Structured style, Phrase/Hybrid sync, session length and the automation options you want. The default autonomous setup is Generative + Phrase-synchronised, with no automatic time limit.
4. Press **PERFORMANCE MODE** in the main toolbar. The application opens the `/eli_lab/v1` OSC receiver, starts the selected local audio capture if requested, enables the generated routing curves and arms AUTO PERFORMANCE.
5. Run **SONATA Expanded** in Sonic Pi. The first transport/start or clock/bar event switches the app to LIVE and starts AUTO PERFORMANCE. SONATA scene changes and phrase cues drive visual variations; energy/cutoff, audio bands and rhythm feed the modulation system.
6. Open View → PROJECTOR OUTPUT → Display N to send the live composition to a second display or projector.
7. Stop SONATA to stop AUTO PERFORMANCE at the patch's transport/stop event. Press **STOP PERFORMANCE MODE** when you want to release resources and restore generated modulation baselines.

Sonic Pi macros are normalized musical control signals, not raw audio samples. For actual audio-band analysis of Sonic Pi output, select the system-loopback device as well. If loopback is unavailable, Sonic Pi transport, energy and cutoff still drive the show. User-created routes and modifiers are preserved; Performance Mode adds missing defaults and disables its generated defaults again when stopped.

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

The **AUDIO / CONTROL** dock includes a configurable OSC receiver for `/eli_lab/v1` (loopback `127.0.0.1:57121` by default). For a live show, press **PERFORMANCE MODE** in the main toolbar; it starts or reuses the receiver, enables the shared reactive curves and arms AUTO PERFORMANCE. Then run SONATA Expanded in Sonic Pi. The receiver can still be started manually for protocol checks:

    python scripts/osc_test_sender.py --host 127.0.0.1 --port 57121

Sonic Pi remains the audio and musical-clock authority. The receiver validates session IDs and monotonically increasing per-session sequence numbers, rate-limits input, and submits normalized events through the bounded M3 control queue. Transport, 1-based bar position, scene/intensity, `energy` and normalized `cutoff` macros, phrase cues and end events are applied on the application tick. The OSC worker never accesses Qt widgets, composition objects or OpenGL resources. Performance Mode combines these macros with optional system-loopback FFT analysis, Modulator Bank followers/envelopes/LFOs, generated layer curves and phrase-aware AUTO PERFORMANCE. See [SONATA integration notes](docs/SONIC_PI_SONATA_INTEGRATION.md) and [M5 Autonomous Performance](docs/M5_AUTONOMOUS_PERFORMANCE.md).

## Effects and overlays

The EFFECTS + OVERLAYS panel controls the master output. Presets are starting looks; every parameter can be adjusted manually. Automated look changes use the same presets and affect the preview and projector output together.

## Sample footage and developer checks

Generate synthetic sample clips:

    python scripts/generate_test_videos.py --output test-footage

Run static checks (the old unit-test suite was removed by request):

    python -m compileall -q main.py config.py core effects generators media rendering ui
    python -m ruff check main.py config.py core effects generators media rendering ui

Windows GitHub Actions runs Python compilation and Ruff. Automated unit-test files and test dependencies have been removed from this repository.

## Project data

The media index, thumbnails and logs are stored under %LOCALAPPDATA%\eli_lab\AV Translator\. Source videos are never copied into a project. .eliav projects store media paths, composition, deck segment settings, effect settings and automation settings.

## Current limitations

- Per-layer effects currently provide a compact shader stack, not an unlimited node graph.
- The first projector implementation uses an independent renderer and CPU frame snapshots; each output uploads textures locally.
- Performance Mode connects Sonic Pi transport, scene and phrase events, energy/cutoff macros, optional loopback audio analysis, Modulator Bank followers/envelopes/LFOs, per-layer curves and phrase-aware AUTO PERFORMANCE. Audio playback remains external. The full 384-bar SONATA rehearsal and Windows loopback/reconnect behaviour still require hardware validation.
- No reverse playback, variable-speed playback, masks, keying, advanced crossfades or recording yet.
- Four simultaneous high-bitrate 1080p/4K clips are not guaranteed on every computer; start with H.264 test clips and check renderer / CPU load.
- The one-file build and third-party notices have not yet received a complete public-redistribution licence review. The bundled visual texture packs also need provenance/redistribution clearance before public release.
- M5 master-output recording and audio/video muxing remain unimplemented; target Lenovo/projector FPS and long-duration rehearsal remain manual validation.
- Projects store absolute media paths. Moving source footage requires re-importing the folder.
