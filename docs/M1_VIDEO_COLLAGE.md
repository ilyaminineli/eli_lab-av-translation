# M1 — Video Collage

## Scope

- Recursive folder scanner and metadata probe.
- SQLite-backed media library.
- Asynchronous thumbnail generation.
- Four independent PyAV video decoders.
- Timestamp-paced playback and bounded latest-frame queues.
- GPU video texture upload.
- Four-layer compositor with position, scale, rotation, opacity and blend modes.
- Random deck assignment and randomized layout with layer locks.
- Media browser, deck controls, layer panel and transport controls.

## First test workflow

1. Launch the application.
2. Add a local folder containing video files.
3. Wait for indexing and thumbnails.
4. Double-click a clip to assign it to the selected deck.
5. Repeat for the other decks.
6. Adjust visibility, opacity and blend mode from the Layers dock.
7. Use Random Set and Randomize Layout.
8. Save a project as .eliav, close the application and reopen it.

## Limitations of the first test build

- Audio playback is not included; video is treated as a visual source.
- Reverse playback, speed control, masks, transitions and external output are not included.
- Playback performance depends on CPU decoding capability and source codec.
- The application currently targets an OpenGL 3.3 Core context.
