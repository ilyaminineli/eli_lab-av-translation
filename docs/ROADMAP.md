# eli_lab AV Translation — Product Roadmap

**Roadmap snapshot:** 4 November 2026  
**Current priority:** finish and harden the video mixer before beginning audio-reactive or external-control work.

## Product goal

Build a dependable Windows-first audiovisual performance instrument: import a large personal footage library, compose four independent video decks into a live GPU canvas, create expressive visual treatments, run semi-random or fully unattended performances, and route the result to a second display or projector.

The roadmap is deliberately staged. M0–M2 establish a complete visual instrument. M3 and M4 add audio and Sonic Pi as control sources. M5 turns the application into a configurable live performance environment.

**Development rule:** do not divert the core effort into M3–M5 until the Video Mixer Completion Gate in this document has been met. The video mixer should be useful, predictable and resilient on its own.

---

## Current implementation snapshot

| Milestone | Current state | Notes |
|---|---|---|
| M0 — Rendering Core | Core implemented; hardware hardening remains | PySide6 shell, OpenGL/ModernGL render contexts, canvas/layers, project persistence and fullscreen external output are present. |
| M1 — Video Collage | Core implemented; reliability pass in progress | Folder indexing, four decoder decks, transforms, blending and random collage behaviour are present. Safe library cleanup, bounded import workers, decoder retirement and preview output limits are now implemented in the hardening branch. |
| M2 — Generative Visuals | Partially implemented | Master GLSL looks, shader overlays, presets, project settings and timed random automation are present. Geometry, particles, waveform visuals and typography generators remain to be delivered. |
| M3 — Audio Reactive Engine | Planned | No audio capture or analysis engine is included in the current video-focused build. |
| M4 — Sonic Pi Integration | Planned | No OSC receiver or Sonic Pi event mapping is included in the current build. |
| M5 — Performance Environment | Planned / foundations only | Full MIDI mapping, scene system, recording and advanced output routing remain future work. |

### Observed machine test

During the November 4, 2026 user test, the application rendered the collage smoothly by user report and the runtime log identified **NVIDIA GeForce RTX 4060** during OpenGL initialization. This confirms that the application initialized on that machine; it is not yet a substitute for a long-duration soak test, multi-monitor reconnect test or performance benchmark.

### Recent reliability and performance hardening

- Thumbnail conversion now makes an owned C-contiguous RGB copy before creating the Qt image; a regression test covers a strided NumPy frame.
- The Media Library has a folder selector and a LIBRARY menu to remove one imported folder, prune missing source files, clear the index, or clean unused thumbnail files. These operations never delete the source videos.
- Folder scans are serialized and thumbnail generation is limited to two background workers, preventing a large import from spawning an unbounded number of simultaneous decode tasks. Destructive library actions are disabled while an import is still indexing.
- Legacy library databases recover imported root paths from the stable collection hash; intentionally imported empty folders remain visible and removable.
- Auto Mode refreshes its eligible source pool when collections are added or removed. Current deck playback is not interrupted; an empty pool simply stops scheduling further random cuts until footage is imported again.
- Decoder replacements use separate frame queues and retain references to workers that have not finished shutting down.
- Preview output is capped at 30 FPS and scaled to a maximum of 1920×1080 before RGB conversion. Smaller sources are not upscaled.
- The renderer reports rolling per-second decode and RGB-conversion cost, render CPU submission time, upload time/bandwidth, active deck count and per-second frame drops. These are diagnostic counters, not GPU timer queries.

The November 4 RTX 4060 screenshot showed approximately 18.9 FPS. The new counters are intended to identify whether the remaining limit is CPU conversion, texture upload or compositor submission. CPU-side timings are not GPU timer-query measurements, so hardware profiling is still required before claiming a specific bottleneck or improvement.

---

# M0 — Rendering Core

## Objective

Provide the stable desktop and GPU foundation on which every video, generator and performance feature is built.

## Implemented

- PySide6 desktop application shell and dockable work panels.
- Qt OpenGL widget with ModernGL rendering.
- Master composition canvas and layer model.
- GPU texture upload and multi-layer framebuffer compositing.
- Independent render contexts for preview and external fullscreen output windows.
- Shared CPU frame snapshots with independent per-window GPU texture uploads.
- .eliav project persistence for the composition and application state.

## Completion and hardening work

- Handle OpenGL context loss, window resize and renderer teardown without leaking resources.
- Test changing display resolution, Windows scaling/DPI, display orientation and primary-monitor selection.
- Handle a projector being disconnected or reconnected while the application is open.
- Make output-window lifecycle deterministic: one selected output, clear close behaviour, safe return to preview.
- Expose useful render diagnostics: actual output size, frame rate, renderer/GPU name and recoverable errors.
- Keep the UI responsive if a render context cannot be initialized.
- Confirm the saved project can be reopened after application restart and after a monitor configuration change.

**M0 exit condition:** preview and external output open, resize, close and reopen reliably; no stale GL resources or frozen UI after repeated operations.

---

# M1 — Video Collage

## Objective

Turn the canvas into a practical four-deck video mixer with a usable footage library and direct control over each source.

## Implemented

- Recursive local folder scanner and video metadata indexing.
- SQLite-backed media library.
- Background thumbnail generation and cached thumbnail paths.
- Four independent PyAV decoder decks with bounded frame queues.
- Per-deck load, play/stop and loop behaviour.
- Random in/out segment playback used by automation.
- Layer visibility, position, scale, rotation, opacity and z-order.
- Normal, Add, Screen, Multiply and Difference blend modes.
- Drag-and-drop folder import into the media browser.
- Random deck assignment and randomized collage layouts.

## Work required to make the mixer dependable

### Media ingest and library

- Make thumbnail conversion stride-safe, as covered by the regression test.
- Show a consistent placeholder and an actionable reason when a thumbnail cannot be produced; a thumbnail failure must never invalidate a playable asset.
- Keep scanning and thumbnail work bounded so importing thousands of clips does not overwhelm memory, worker threads or disk I/O.
- Prevent duplicate concurrent scans of the same folder and provide clear scan progress, cancellation and failure states.
- Revalidate missing or moved media paths and provide a relink workflow.
- Separate unsupported, corrupt and temporarily unavailable media states in the browser.
- Add search, sorting, collection filtering, favourites and a clear way to inspect clip metadata.

### Deck playback

- Make decoder shutdown, replacement and restart race-safe; old workers must not publish frames into a newly loaded deck.
- Test variable-frame-rate footage, long-GOP codecs, unusual frame sizes, rotation metadata and clips with no usable video stream.
- Provide robust end-of-file behaviour for both looping and one-shot playback.
- Add precise seek / scrub, frame stepping, pause and resume.
- Add playback speed and reverse playback only after timestamp and decoder behaviour can be kept correct.
- Define an explicit aspect policy: Fit, Fill/Crop and Stretch, with predictable source and canvas aspect handling.
- Keep playback state, duration, segment in/out and error state visible in the deck UI.
- Ensure one bad decoder cannot stall the other three decks or the render loop.

### Mixer and composition controls

- Make layer selection and deck-to-layer relationships obvious.
- Improve direct manipulation of position, size and rotation, including reset and fit-to-canvas actions.
- Provide predictable opacity and blend-mode controls with useful visual feedback.
- Add per-deck mute/hide/hold/freeze controls for visual operation (not audio muting).
- Add a practical transition model: hard cut first, followed by dissolve and selected stylized transitions.
- Make random composition choices reproducible when the user requests a seeded or saved run.

**M1 exit condition:** a user can load and mix four representative sources, make manual adjustments, save/reopen a composition, and continue playback without UI freezes, decoder cross-talk or unexplained loss of a deck.

---

# M2 — Generative Visuals

## Objective

Give the video mixer a distinctive visual toolkit and make automated performances feel composed rather than merely shuffled.

## Implemented foundations

- GPU master post-processing pass after the layer compositor.
- Brightness, contrast, saturation and gamma.
- Vignette, grain, scanlines, RGB split / chromatic aberration and glitch.
- Pixelation, posterization and inversion.
- Built-in Clean, 16mm Film, VHS / Tape, CRT, Bleach Bypass, Dream Haze and Digital Damage looks.
- Effect and automation settings saved in .eliav projects.
- Semi-random collage layouts and timed effect-look changes.
- Unattended automation sessions with a selected duration or manual stop.

## Generators still to implement

### Geometry

- Procedural 2D shapes, lines, grids, rings, polygons and parameterized patterns.
- Geometry layers with independent transform, opacity, blend mode and compositing order.
- Animated parameters driven by envelopes, oscillators, deterministic random sources and scene state.
- GPU-friendly batching and instancing so dense patterns do not create large CPU draw-call overhead.

### Particles

- GPU-oriented particle system with controlled count, lifetime, velocity, acceleration, size and colour.
- Emission from points, lines, shapes and sampled image/video regions.
- Forces such as turbulence, attraction, repulsion, orbit and drag.
- Presets that are visually distinct but bounded in their resource use.
- Seeded randomness so scenes can be recalled and tested.

### Waveform and signal visuals

- Procedural waveforms and oscilloscope-style graphics that work without an audio source.
- Configurable traces, grids, phase patterns and Lissajous-style forms.
- In M3, allow the same visualizers to subscribe to live audio bands or beat events without coupling the generator to the audio input device.

### Typography

- Text layers with editable content, font, weight, tracking, leading, alignment and colour.
- Layout anchors, safe areas, rotation, scale and opacity.
- Motion behaviours such as reveal, crawl, type-on, jitter and timed entrance/exit.
- Project-safe font fallback and clear handling of missing fonts.
- Text remains a first-class layer, not an image permanently baked into the master frame.

### Effect and overlay system

- Keep the current master look pass as a reliable base.
- Add a controlled stack of effect stages with documented order and parameter ranges.
- Support per-layer effects where practical, while keeping expensive global effects in the master pass.
- Add reusable, saveable visual presets and user-defined preset collections.
- Add alpha-capable still-image overlays and animated overlay media as distinct, reorderable layers.
- Support blend, opacity, transform, in/out timing and optional automation for overlays.
- Give users a bypass / compare control and a one-action reset to a neutral image.

**M2 exit condition:** a saved composition can combine video decks, generated geometry, particles, typography and overlays; its looks can be adjusted manually or varied by automation; the same composition renders consistently in preview and projector output.

---

# Video Mixer Completion Gate — Priority Before M3

This is the immediate delivery track. It closes the gap between a promising live prototype and a dependable visual performance tool.

## Gate A — Reliability first

1. Fix and regression-test the non-contiguous thumbnail buffer error.
2. Make media scanning and thumbnail generation resilient to large folders and individual bad files.
3. Verify decoder replacement, EOF, one-shot segments, loop boundaries and shutdown.
4. Make all worker-thread ownership and cancellation explicit.
5. Ensure errors are visible and local to the failed asset/deck, never fatal to the session.
6. Exercise project save/load with missing footage, moved paths and older schema versions.

## Gate B — Finish the hands-on mixer

1. Complete the deck transport controls and clear visual feedback.
2. Add Fit / Fill / Stretch and predictable transforms.
3. Improve layer selection, ordering, lock, hide and per-layer blend controls.
4. Add hold/freeze and a small, reliable transition set.
5. Make the media library practical to search and curate.
6. Keep preview and projector output frame-consistent.

## Gate C — Make Auto Mode a real instrument

The existing random mode is a foundation. It should mature into a controllable director with:

- A selectable source pool and per-deck include/exclude rules.
- Independent deck timing, segment length and loop/one-shot behaviour.
- Weighted clip selection with no immediate repeats where the pool allows.
- Cut pacing profiles and user-defined minimum / maximum timing.
- Layout families with intensity / complexity controls.
- Effect and overlay variation with intensity limits and cooldowns.
- Lock, hold and manual override behaviour that automation always respects.
- Scene-aware choices so a session has coherent changes rather than unrelated parameter noise.
- Optional deterministic seed and a record of the last automated action.
- Session duration, pause/resume and safe stop that does not abruptly black out the composition.
- A quick “re-roll this deck / layout / look” action for live intervention.

Automation must never overwrite locked content, exceed configured safety ranges or block the UI while loading media.

## Gate D — Visual identity and control

- Polish the mixer UI into a deliberate VJ surface: clear deck status, strong hierarchy, compact transport and useful meters/indicators.
- Add a small set of high-quality, coherent visual presets before adding dozens of shallow effects.
- Give every generator and effect sensible defaults and an obvious bypass.
- Make overlays and typography easy to edit during playback.
- Provide feedback for active automation, current look, current layout and remaining session time.

## Gate E — Performance and hardware validation

- Measure preview and projector frame rate independently.
- Record decode latency, dropped frames, queue depth and GPU render time.
- Stress-test four concurrent clips at 1080p H.264, then test representative higher-resolution footage.
- Test 30-minute and 60-minute unattended sessions.
- Test repeated projector open / close, display disconnect / reconnect and window resizing.
- Check memory, thread count and GPU resources before and after a long run.
- Keep a graceful reduced-load mode for machines that cannot decode four demanding sources simultaneously.

**Video Mixer release criterion:** all gates above have been exercised on Windows hardware, critical errors are resolved, a 60-minute run completes without degradation, and the user can recover from a bad media file or output-display change without restarting the application.

---

# M3 — Audio Reactive Engine

## Objective

Introduce audio as an optional analysis and modulation source without making the video engine depend on audio being enabled.

## Planned implementation

- Audio input device selection and device-change handling.
- Live input capture with clear permission and unavailable-device states.
- FFT analysis and configurable low, mid and high frequency bands.
- RMS / amplitude envelope, transient detection and beat / tempo estimation.
- Smoothing, sensitivity, attack and release controls.
- Modulation matrix routing audio signals to effect, generator, layer and automation parameters.
- Mapping curves, ranges, inversion, hold and per-route enable/bypass.
- Audio visualizers that can consume the same analysis bus.
- Test signals and recorded fixtures so the engine can be tested without a microphone or external sound source.

**M3 exit condition:** audio devices can be changed safely, analysis remains stable over long sessions, and each modulation route can be inspected and disabled independently.

---

# M4 — Sonic Pi Integration

## Objective

Allow Sonic Pi to control the visual instrument through a documented, versioned OSC protocol.

## Planned implementation

- OSC receiver with configurable bind address and port.
- Explicit event namespace rather than undocumented one-off message names.
- Parameter translation and range normalization.
- Beat, bar, cue and scene events.
- Mapping from OSC events to effects, generators, deck actions and automation scenes.
- Connection / heartbeat status, message logging and malformed-packet handling.
- A local test sender and documented example Sonic Pi snippets.
- Optional beat synchronization and quantized scene switching.

**M4 exit condition:** the protocol is documented, testable without Sonic Pi, resilient to missing or malformed messages and does not block video rendering.

---

# M5 — Performance Environment

## Objective

Package the visual, audio and external-control systems into a flexible live performance workflow.

## Planned implementation

- MIDI device discovery and controller mapping.
- Learn mode, per-control scaling, pickup behaviour and mapping persistence.
- Scene and preset banks with recall, morphing and quantized transitions.
- Preset overlays and macro controls for high-impact live changes.
- Recording of the master output with configurable format, frame rate and destination.
- Output routing improvements for preview, projector and additional supported outputs.
- Performance mode with a simplified, low-distraction control surface.
- Save/load complete performance sets and restore the last known-good state.
- Optional event and performance recording for repeatable sessions.

**M5 exit condition:** a set can be prepared, saved, recalled and performed from a compact control surface with stable recording and output behaviour.

---

## Engineering principles across all milestones

1. **Rendering must stay isolated.** Decoder, audio and OSC workers publish data; only the relevant render context owns and changes its GPU resources.
2. **Bound every queue.** No unbounded frame, event or analysis buffers in a long-running session.
3. **Keep the UI non-blocking.** File scanning, thumbnail generation, decoding, audio capture and OSC I/O must not run synchronously on the main UI thread.
4. **Prefer recoverable failure.** A broken file, lost input device or disconnected output should be isolated and reported, not crash the whole performance.
5. **Persist intent.** Projects and performance sets should store user-facing settings and stable identifiers, not transient GPU objects or worker state.
6. **Make automation explainable.** Show what changed, when, and why; respect locks and manual overrides.
7. **Test the seams.** Cover worker replacement, device changes, project compatibility, timing boundaries and preview/output synchronization.
8. **Optimize from measurements.** Add diagnostics before choosing frame dropping, resolution scaling or decoder concurrency policies.

## Immediate next implementation order

1. Validate the thumbnail fix, folder removal and full-library reset on Windows; add cancellation and better progress for very large imports.
2. Measure the new CPU/upload/drop counters with the user's representative four-clip composition and compare preview-only vs projector output.
3. Finish decoder lifecycle tests and add explicit end-of-stream, seek and variable-frame-rate fixtures.
4. Mixer ergonomics: aspect handling, layer selection, hold/freeze and transitions.
5. Auto Mode refinement: weighted selection, cooldowns, manual override and scene coherence.
6. M2 geometry, particles, waveform visuals, typography and alpha-capable overlay layers.
7. Projector / 60-minute soak testing and performance diagnostics.
8. Declare the Video Mixer complete only after the release criterion is met; then begin M3.

This order is intentional: the goal is to finish a polished, expressive and reliable video instrument—not to start the audio roadmap while the visual foundation is still being hardened.
