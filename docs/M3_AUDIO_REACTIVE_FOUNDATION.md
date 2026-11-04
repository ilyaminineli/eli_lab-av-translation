# M3 — Audio-Reactive Engine and Performance Control Foundation

## Purpose

M3 adds a source-independent control layer between incoming performance signals and the visual instrument. Audio analysis is the first live signal source. The same normalized event/state contract will later accept Sonic Pi OSC in M4, without letting audio or network code call Qt widgets or OpenGL.

The intended flow is:

```text
Audio input / loopback / internal test source
                  │
                  ▼
         Source-specific adapter
                  │
                  ▼
       Validated ControlEvent contract
                  │
                  ▼
          Bounded event queue
                  │
                  ▼
       Application/UI-thread drain
                  │
                  ▼
       Performance transport + scene
           + intensity + macros
                  │
                  ▼
        M3 modulation / target map
                  │
                  ▼
      Existing layer, effect, generator
          and automation models
                  │
                  ▼
            GPU renderers
```

M3 does not introduce a second renderer, audio playback engine or network protocol.

## Implemented foundation slice

The first M3 code slice now provides:

- A validated `ControlEvent` data contract with source, event kind, payload, sequence, session ID and receive timestamp.
- A bounded, thread-safe `ControlEventQueue`; producers never block the render loop when the queue is full.
- A `PerformanceControlState` for BPM, beats per bar, beat/bar position, transport running state, scene ID, normalized intensity, named normalized macros and the last cue.
- Sequence de-duplication scoped to source and session ID.
- Validation of tempo, clock, intensity and macro ranges.
- UI-thread draining from the existing application tick.
- A compact control-status readout in the application status bar.

This is a data/control foundation only. It does not yet capture audio or apply control macros to visual parameters.

## Remaining M3 work

### 1. Audio source layer

- Select an input device or supported system-loopback source.
- Handle device loss, reconnect and device switching without stopping video playback.
- Show source state, sample rate, channel count and capture errors.
- Keep capture in a dedicated worker with explicit ownership and cancellation.
- Make audio input optional; a missing device must never block the visual mixer.

### 2. Analysis bus

- RMS / amplitude envelope.
- Low, mid and high frequency-band energy.
- Transient/onset strength.
- Optional beat and tempo estimate with confidence.
- Configurable smoothing, sensitivity, attack and release.
- A synthetic signal source and recorded test fixtures so tests do not require a microphone or live audio device.

### 3. Modulation matrix

Route normalized sources to approved visual targets. Each route needs:

- Source and target identifiers from explicit registries.
- Minimum/maximum output range.
- Curve (linear, exponential, stepped or custom preset).
- Smoothing / attack / release.
- Invert, hold and bypass.
- Intensity ceiling.
- Lock and manual-override respect.
- Current input/output values for inspection.

The first targets should be deliberately small: master-look parameters, generator motion/density, selected layer opacity/transform and Auto Performance intensity/timing. Do not expose arbitrary Python attribute names or direct shader uniforms as routes.

### 4. Transport and scene controls

The state model already supports the core transport and scene fields. Finish this surface with:

- Internal test clock and a selectable clock authority.
- BPM, beats-per-bar, beat and bar status.
- Scene selection and normalized intensity.
- Named macros and cue/phrase events.
- Quantized changes at the next beat, bar or phrase boundary.
- Clear source ownership so a future external clock can become authoritative without two clocks fighting.

For the SONATA patch, M4 will provide the external 92 BPM / 4-beat-bar clock. M3 should not assume the final external source is an audio beat detector.

### 5. Persistence and rehearsal

- Persist user-authored mappings and scene profiles, not live device handles or transient analysis buffers.
- Add a deterministic test/replay source for event sequences.
- Add a small, visible monitor for source, BPM, bar, scene, intensity and macro values.
- Keep an event history with timestamps and source labels, with a bounded history size.

## M3 exit criteria

M3 is complete when:

1. An audio source can be selected, lost and restored without interrupting the video session.
2. Analysis outputs are stable, bounded and visible.
3. Test/replay mode produces the same normalized control events as a live source.
4. Modulation routes are independently inspectable, bypassable and range-limited.
5. Locks and manual overrides always take precedence.
6. No audio worker, event source or analysis callback performs Qt widget work or OpenGL calls.
7. Projects can save and restore mapping configuration.
8. The transport/scene/macro contract is ready for M4 without changing the renderer.

## Explicitly out of scope for M3

- Sonic Pi OSC receiver and patch modifications (M4).
- MIDI learn/controller mapping (later performance-environment milestone).
- Audio playback or DAW functionality.
- Direct arbitrary remote control of Python methods, paths or shader uniforms.
