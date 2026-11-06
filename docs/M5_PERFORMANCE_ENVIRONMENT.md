# M5 — Performance Environment

## Scope

M5 connects the M3 transport/audio layer, M4 Sonic Pi bridge, per-layer modifier stacks, Modulator Bank and AUTO PERFORMANCE into a one-button autonomous show. Press PERFORMANCE MODE, then run SONATA in Sonic Pi. The first transport/start or clock/bar event starts the armed generative session; phrase and scene cues drive visual changes. The existing normalized mapping contract remains shared across video layers, geometry, text, waveform, particles, animated overlays and AUTO PERFORMANCE.

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

## Autonomous Performance Mode

See [M5 Autonomous Performance](M5_AUTONOMOUS_PERFORMANCE.md) for the full operator sequence. The mode starts or reuses OSC, optionally starts loopback capture, enables generated default routes/modulators/layer curves, and waits for Sonic Pi. Sonic Pi energy/cutoff and scene/phrase events are enough to drive the visual performance even when no audio device is selected. A system-loopback device adds real audio-band/onset analysis.

The default global routes cover master look, clip switching, cut timing, segment length and automation intervals. Per-layer AUTO curves cover video, geometry, text, waveform, particles and animated overlays. Defaults are stable-ID and non-destructive: custom routes are kept, generated mappings are disabled when the mode stops, and saving an active show stores those generated mappings disabled.

AUTO PERFORMANCE supports random, structured and generative styles with time, bar, phrase and hybrid sync. Phrase mode uses musical cues instead of a parallel wall-clock randomizer. If the footage pool is empty, generative layers, text, effects and layout automation can still run.

## MIDI controls

The optional MIDI adapter uses `mido`; it does not make MIDI hardware a startup dependency. Device discovery is explicit. Port callbacks enqueue compact normalized events into a bounded queue; the application tick drains them and applies mappings outside the callback. The AUDIO / CONTROL panel exposes discovery, connect/disconnect, Learn Next Controller, a target selector, per-mapping range/curve/pickup editing, and mapping update/removal.

Mappings support CC, note and pitch wheel messages, device/channel/number filters, target IDs, min/max scaling, linear/smoothstep/exponential curves and pickup. Pickup holds until the incoming physical control crosses or approaches the current virtual value. Mapping definitions persist, but physical positions and pickup latch state do not. Device loss is local and does not stop the performance.

Stable mapping target IDs include `macro.<name>`, `transport.tempo`, `scene.intensity`, `automation.<field>`, `master.<field>` and `layer.<layer-id>.<target-id>`. MIDI learn is a UI operation that captures the next matching event and creates a mapping; it must never infer a target silently.

## Scenes, morphing and presets

A performance scene is a named snapshot of composition, effects, AUTO PERFORMANCE settings, transport and normalized control state. The scene-bank UI supports capture, removal, immediate/beat/bar/phrase recall and a configurable numeric morph duration. Recall uses the existing transport scheduler. Numeric-compatible targets interpolate using smoothstep; discrete composition/media state switches at the cue. Currently locked layers are retained.

Scene banks are project-level definitions. A complete `.eliset` contains composition, deck states, master effects, AUTO PERFORMANCE settings, transport/audio settings, global modulation routes, Modulator Bank, MIDI mappings and scene snapshots. It is separate from `.eliav`, allowing one composition to be reused across live sets.

## Recording and outputs

The master OpenGL output is the authoritative composed image for preview and projector. Recording belongs after composition so it includes generators, overlays, blend modes and master effects. A production recorder must use bounded immutable frame handoff and a dedicated encoder worker; Qt paint and UI callbacks must not perform blocking encoding.

Codec/format selection, audio muxing, frame pacing and hardware acceleration are not implemented in this increment and require target-machine validation. A successful software save operation is not sufficient to claim projector capture or A/V sync is signed off.

## Compact performance surface

The main toolbar now has a one-button Performance Mode control and the AUDIO / CONTROL panel displays OFF/ARMED/LIVE/DEGRADED state, MIDI mappings and the performance scene bank. A dedicated compact show surface with scene navigation, macro controls, output selection and recording status remains to implement. Detailed media editing, generator authoring and modulation graph editing stay in the existing docks.

## Verification

The repository unit-test suite and pytest dependencies were removed at the user's request. Current CI performs Python compilation and Ruff checks only; it does not execute runtime or hardware tests. Manual target-machine checks remain required for MIDI hot-plug, physical fader pickup, sustained recording and preview/projector synchronization.

M5 is complete only when a prepared set can be recalled and performed from a compact surface with stable recording and output behaviour on the target machine.