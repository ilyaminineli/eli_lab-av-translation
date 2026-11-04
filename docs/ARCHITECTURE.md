# Architecture

## Product direction

eli_lab AV Translation is a Windows-first live video collage and VJ performance environment. Its first unattended workflow is: import a local footage folder, run randomized clip segments across four decks, change collage arrangements and master effect looks automatically, and send the master output to a separate fullscreen display.

## Runtime boundaries

- UI owns Qt widgets, automation controls and output-window lifecycle.
- Application core owns composition, project state, events, automation scheduling and orchestration.
- Media owns discovery, metadata, thumbnails, frame queues, video decks and decoding.
- Rendering owns OpenGL resources, video textures, layer compositing and post-processing.
- Effects owns master look parameters and filter presets.
- Performance control owns normalized transport, scene, intensity, macro and cue state.
- Future audio-analysis and OSC adapters publish normalized control events; they do not replace the renderer.

Decoder workers must never call OpenGL. They publish timestamped CPU frames to bounded queues. The main application refreshes a shared latest-frame snapshot cache. Each output renderer independently uploads new revisions into its own OpenGL context.

## Rendering lifecycle

1. Qt creates a QOpenGLWidget context for the preview or projector window.
2. PerformanceView.initializeGL creates a per-window ModernGL wrapper and compositor.
3. Each VideoDecoder worker decodes frames into a bounded queue.
4. The application refresh loop consumes each queue once and stores a FrameSnapshot.
5. Each PerformanceView reads the current snapshots without consuming the queues.
6. Each RenderEngine uploads only unseen frame revisions to its local GPU textures.
7. The compositor blends visible video layers into ping-pong framebuffers.
8. A master GLSL effect pass applies the current look / overlay parameters.
9. The final framebuffer is drawn into that output window's Qt framebuffer.

The preview and projector windows share application state and CPU frame snapshots, not OpenGL texture objects.

## Automation lifecycle

AutomationDirector uses monotonic deadlines for each deck, layout change, effect-look change and session expiry. It is ticked by the application/UI timer. It accepts an RNG seed for deterministic tests.

## Performance control plane

M3 introduces a renderer-independent control contract in `core/performance_control.py`:

1. Source adapters create validated `ControlEvent` messages.
2. Events enter a bounded, thread-safe `ControlEventQueue`.
3. The normal application/UI tick drains a bounded batch and applies it to `PerformanceControlState`.
4. The state exposes transport (BPM, meter, beat/bar), scene, normalized intensity, named macros and cues.
5. Future M3 modulation routes map these values to explicitly registered visual targets with ranges, smoothing, bypass, locks and manual-override precedence.

The current first slice implements the event/state boundary and status display. It does not yet include audio capture, FFT analysis or visual target routing.

Adapters must not mutate composition or UI state from worker threads. OSC and audio workers publish events only; application-owned state changes happen in the controlled application tick. Rendering reads the resulting normal composition/effect/generator model and remains unaware of the source protocol.

## Project data

A project file uses the .eliav extension and UTF-8 JSON. Schema version 2 stores composition, deck assignments, segment in/out points, loop settings, effect settings and automation settings. M3 mapping/profile persistence will be added when those user-facing settings are implemented; transient live transport and source state are not project data.

## Future extensions

- M3 audio analysis, transport/scene state and modulation routing.
- M4 versioned Sonic Pi OSC event bridge and visual action mapping.
- MIDI mapping, performance banks, recording and advanced output routing.
