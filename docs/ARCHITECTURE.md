# Architecture

## Product direction

ELI LAB AV Translation is a Windows-first live audiovisual compositor. Its first useful workflow is video collage: index a local footage folder, load clips into four independent decks, compose them as GPU layers and randomize the scene during a performance.

The rendering pipeline is deliberately independent from the UI and media decoders.

## Runtime boundaries

- UI (ui/) owns Qt widgets and user interaction.
- Application core (core/) owns composition, project state, events and orchestration.
- Media (media/) owns discovery, metadata, thumbnails, frame queues and decoding.
- Rendering (rendering/) owns OpenGL resources, video textures and compositing.
- Future modules (audio/, generators/, effects/, integrations/, presets/) feed the same layer/compositor model.

Decoder workers must never call OpenGL. They publish timestamped CPU frames to bounded queues. The Qt OpenGL widget consumes the newest frame and uploads it while its context is current.

## Rendering lifecycle

1. Qt creates the QOpenGLWidget context.
2. PerformanceView.initializeGL creates the ModernGL wrapper and compositor.
3. VideoDecoder workers decode frames into bounded queues.
4. PerformanceView.paintGL consumes the newest frame from each deck.
5. RenderEngine uploads changed frames to GPU textures.
6. Compositor composites visible layers into ping-pong framebuffers.
7. The final texture is drawn into Qt's current widget framebuffer.

## Project data

A project file uses the .eliav extension and JSON content. It stores composition metadata, layers, deck assignments and source paths. It does not copy media files into the project.

## Future extensions

- M2: procedural generators, GLSL effects and preset compositions.
- M3: audio input, FFT, beat/onset analysis and modulation routing.
- M4: Sonic Pi OSC event bridge and visual action mapping.
- M5: MIDI mapping, external video output and recording.
