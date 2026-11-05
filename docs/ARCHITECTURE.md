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

M3 adds a renderer-independent control layer across the performance-control, transport, audio-analysis, audio-capture and modulation modules.

1. Source adapters create validated ControlEvent messages.
2. Events enter a bounded, thread-safe ControlEventQueue.
3. The normal application/UI tick drains a bounded batch and applies it to PerformanceControlState.
4. InternalTransport advances from monotonic deadlines; it emits beat/bar events and quantized scene changes without a sleeping clock thread.
5. The SoundCard worker owns the active input/loopback recorder, analyzes captured blocks and publishes into a bounded latest-frame queue.
6. The application tick consumes audio feature snapshots (RMS, peak, low/mid/high, onset and optional tempo/confidence) and combines them with transport and named macro sources.
7. ModulationMatrix maps only registered sources to registered visual targets with safe ranges, curves, smoothing, bypass, hold, intensity ceilings, layer locks and manual-override precedence.
8. Resulting values update existing effect/layer/generator/automation models. Renderers remain unaware of SoundCard, input devices or any source protocol.

Audio workers never call Qt widgets or OpenGL. Device loss is isolated to the capture service; the video session continues. Synthetic and fixture-replay sources use the same analysis path as hardware input.

## Scene profiles

SceneProfileRegistry stores user-facing scene IDs, intensity, master look and Japanese colour palette. The initial profiles match the 16 scene IDs in the SONATA patch. Scene changes may apply immediately or be quantized to a beat, bar or phrase boundary. M4 OSC will publish normalized events into the same control contract rather than directly mutating visual objects.

## Project data

A project file uses the .eliav extension and UTF-8 JSON. Schema version 2 stores composition, deck assignments, segment in/out points, loop settings, effect settings and automation settings. User-facing M3 transport configuration, analysis settings, modulation routes and scene profiles are persisted; transient live transport position, source handles and audio buffers are not project data.

## Future extensions

- M4 versioned Sonic Pi OSC event bridge and visual action mapping.
- MIDI mapping, performance banks, recording and advanced output routing.
