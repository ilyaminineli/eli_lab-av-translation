# M2 — Automated Collage, Effects and Projector Output

## Purpose

M2 turns the four-deck video mixer into an unattended VJ instrument. The operator imports a footage folder, chooses a pacing profile and session length, starts automation, and can send the master composition to a separate monitor or projector.

This milestone deliberately focuses on video, effects and automation. Audio and Sonic Pi integration remain separate work.

## Automated video direction

Each unlocked deck receives its own random in/out segment:

- A segment start is chosen within the source clip's duration.
- Segment length is selected from the chosen short, mixed or long range.
- A deck randomly loops that segment or plays it once.
- A per-deck cut timer chooses when to load a new clip or another segment from the current clip.
- The clip-switch probability controls how often the director changes source files rather than selecting another section of the current file.

Locked decks are skipped. The automation session does not stop playback when its timer expires; it simply stops scheduling new changes.

## Semi-random collage

The director cycles among a family of arrangements:

- Four-panel grid.
- Full-frame base with picture-in-picture accents.
- Horizontal split.
- Vertical split.
- Asymmetric collage.
- Centered / stacked layers.

A small position jitter, scale variation, opacity and blend-mode choice prevent every cycle from looking identical. Locked layers are left alone.

## Effect and overlay pass

The master compositor runs one GPU post-processing pass after video layers are composited.

Available controls:

- Brightness, contrast, saturation and gamma.
- Vignette and film grain.
- Scanlines and RGB split / chromatic aberration.
- Horizontal signal glitch.
- Pixelation and posterization.
- Color inversion.

Built-in looks are parameter presets. They are intentionally editable rather than baked video effects.

## Session controls

The automation panel exposes:

- Footage pool: all indexed folders or one imported folder.
- Session length: 30, 45, 60, 90 or 120 minutes, or until stopped.
- Cut rhythm: slow, balanced or fast.
- In/out length: short, mixed or long fragments.
- Loop probability: occasional, mixed or frequent.
- Automatic layout and look changes: independently enabled.

The director uses monotonic time for scheduling. UI repaint rate does not change the chosen cut intervals.

## Separate output window

The output window is a separate fullscreen Qt top-level window placed on the selected QScreen. Each window owns its own QOpenGLWidget, ModernGL context, GPU textures and renderer resources.

Decoders are not duplicated. The application collects each deck's latest CPU frame once into a shared snapshot cache. The preview and projector renderers each track their own frame revision and upload a new snapshot into their own GPU context.

This avoids two output windows racing to consume one decoder queue and avoids relying on cross-window OpenGL texture sharing.

Use View → PROJECTOR OUTPUT → Display N to open the output. Press Escape on the output display to close it.

## Project persistence

Project schema version 2 stores:

- Deck source paths and media IDs.
- Segment in/out points and loop state.
- Master effect parameters and selected look.
- Automation settings.

The project loader still accepts schema version 1 projects; their missing M2 settings use defaults.

## Validation

Unit tests cover random segment bounds, locked deck behavior, scheduled cuts, session expiry, effect preset reset and M2 project-state persistence.

A physical Windows multi-display test is still required to validate monitor placement, GPU driver behavior and four-stream playback on the target performance computer.
