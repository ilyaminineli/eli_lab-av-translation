# M5 — Performance Environment

## Scope

M5 turns the M3 transport/audio layer, M4 Sonic Pi bridge, per-layer modifier stacks and Modulator Bank into a repeatable live-show workflow. The existing normalized mapping contract remains the shared model across video layers, geometry, text, waveform, particles, animated overlays and AUTO PERFORMANCE.

## Unified mapping coverage

| Domain | Supported target families |
|---|---|
| Composition geometry | opacity, position X/Y, scale, rotation |
| Procedural geometry | motion speed/amount, density, rotation |
| Text Art | animation speed/amount, font size, letter spacing |
| Waveform | amplitude and frequency |
| Particles | speed, size, spread, trails |
| Animated overlays | playback speed and frame hold |
| AUTO PERFORMANCE | cut/segment timing, layout/effect/generator intervals, loop/switch probability |
| Master output | global modulation matrix effect targets |

Audio bands, onset/beat confidence, normalized transport phases/pulses, scene intensity, Sonic Pi energy/cutoff and Modulator Bank sources are shareable inputs. A target is offered only when its owner can apply it. Per-layer modifiers retain their current baseline, lock, manual override and ownership rules.

## MIDI controls

The optional MIDI adapter uses `mido`; it does not make MIDI hardware a startup dependency. Device discovery is explicit. Port callbacks enqueue compact normalized events into a bounded queue; the application tick drains them and applies mappings outside the callback. The AUDIO / CONTROL panel exposes discovery, connect/disconnect and a basic CC 1 → `macro.energy` mapping action. The full learn-target editor and mapping inspector remain future work.

Mappings support CC, note and pitch wheel messages, device/channel/number filters, target IDs, min/max scaling, linear/smoothstep/exponential curves and pickup. Pickup holds until the incoming physical control crosses or approaches the current virtual value. Mapping definitions persist, but physical positions and pickup latch state do not. Device loss is local and does not stop the performance.

Stable mapping target IDs include `macro.<name>`, `transport.tempo`, `scene.intensity`, `automation.<field>`, `master.<field>` and `layer.<layer-id>.<target-id>`. MIDI learn is a UI operation that captures the next matching event and creates a mapping; it must never infer a target silently.

## Scenes, morphing and presets

A performance scene is a named snapshot of a prepared state. Recall supports immediate, beat, bar and phrase scheduling via the existing transport. Numeric-compatible parameters can morph using smoothstep interpolation; discrete media, pattern, font, blend-mode and scene changes switch at the quantized boundary. Layer locks and manual overrides remain authoritative.

Scene banks are project-level definitions. A complete `.eliset` contains composition, deck states, master effects, AUTO PERFORMANCE settings, transport/audio settings, global modulation routes, Modulator Bank, MIDI mappings and scene snapshots. It is separate from `.eliav`, allowing one composition to be reused across live sets.

## Recording and outputs

The master OpenGL output is the authoritative composed image for preview and projector. Recording belongs after composition so it includes generators, overlays, blend modes and master effects. A production recorder must use bounded immutable frame handoff and a dedicated encoder worker; Qt paint and UI callbacks must not perform blocking encoding.

Codec/format selection, audio muxing, frame pacing and hardware acceleration are not implemented in this increment and require target-machine validation. A successful software save operation is not sufficient to claim projector capture or A/V sync is signed off.

## Compact performance surface

The existing AUDIO / CONTROL panel now provides MIDI discovery/connect and a one-action starter mapping. A compact show surface with scene-bank navigation, macro controls, Auto Performance and recording/output status remains to implement. Detailed media editing, generator authoring and modulation graph editing stay in the existing docks.

## Verification

Unit tests cover mapping normalization/scaling/pickup, morph interpolation and versioned atomic performance-set persistence. Manual target-hardware checks remain required for MIDI hot-plug, physical fader pickup, sustained recording and preview/projector synchronization.

M5 is complete only when a prepared set can be recalled and performed from a compact surface with stable recording and output behaviour on the target machine.