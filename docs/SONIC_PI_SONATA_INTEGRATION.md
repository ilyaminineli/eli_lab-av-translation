# SONATA Expanded — Sonic Pi / AV Translation Integration Notes

## Source inspected

Repository: `ilyaminineli/sonicpi_eli_lab`  
Patch: `04_LIVE/SEULPIRLEAMBACY/SONATA_expanded.rb`

This document records the requirements exposed by the actual live patch. It is an integration design note, not a claim that OSC is already implemented in the patch.

## What the patch does today

- Tempo: **92 BPM**.
- Meter assumed by its clock: **4 beats per bar**.
- Form: **384 bars**, approximately **16 minutes 42 seconds** at 92 BPM.
- Structure: **16 scene changes**, including the final `end` scene.
- Internal complexity: **93 live loops** plus a form thread and helper functions.
- The musical patch uses Sonic Pi's own `set/get` state and `cue/sync` events.
- The bar clock increments `sp_b_count`, cues `sp_b`, then sleeps for four beats.
- Scene changes update `sp_sc` and `sp_int`, then cue `sp_sc_change`.
- A synchronized macro loop updates `sx_m_e` (energy), `sx_m_c` (filter cutoff) and `sx_macro_phr` (phrase index).
- The patch references a local sample root on drive `F:`; those samples belong to Sonic Pi and do not need to be indexed by AV Translation.

**Important:** the inspected file contains no `osc`, `osc_send` or `use_osc` calls. Its cues are internal to Sonic Pi. M4 therefore needs a small outbound OSC sender added at the musical control points.

## The 16 scene states

| Scene ID | Duration | Intensity |
|---|---:|---:|
| `in` | 16 bars | 0.12 |
| `exp` | 24 bars | 0.28 |
| `tm_a` | 24 bars | 0.45 |
| `trns` | 16 bars | 0.34 |
| `dev` | 32 bars | 0.62 |
| `fr` | 32 bars | 0.84 |
| `ssp` | 24 bars | 0.24 |
| `rtrns` | 16 bars | 0.46 |
| `rc` | 16 bars | 0.70 |
| `rc_w` | 40 bars | 1.00 |
| `peak` | 56 bars | 1.00 |
| `intd` | 24 bars | 0.30 |
| `s_s` | 28 bars | 1.00 |
| `rls` | 24 bars | 0.42 |
| `c` | 12 bars | 0.14 |
| `end` | — | 0.00 |

The form totals 384 bars before the final end marker. `sp_b_count` increments before `sp_b` is cued, so OSC `bar_index` should preserve the patch's **1-based** bar count. The scene IDs should be treated as stable symbolic names; their visual meaning should be configured in AV Translation rather than inferred from the abbreviations.

## Control values worth transmitting

| Patch value | Meaning in the patch | Proposed AV representation |
|---|---|---|
| `use_bpm 92` | Musical tempo | Transport BPM |
| `sp_b_count` | Monotonic bar counter | Bar position / clock |
| `sp_sc` | Current section ID | Scene selection |
| `sp_int` | Section intensity, 0–1 | Scene intensity |
| `sx_m_e` | Evolving energy, 0–1 | Macro `energy` |
| `sx_m_c` | Evolving filter cutoff, roughly 48–118 | Macro `cutoff`, normalized to 0–1 |
| `sx_macro_phr` | Phrase index, bar divided by four | Phrase cue/index |
| `sp_fin` | Internal end cue | Transport stop / end cue |

For the cutoff macro, the proposed normalization is:

`cutoff_normalized = (sx_m_c - 48.0) / 70.0`

clamped to 0–1. This preserves the relative sweep without pretending that a visual parameter literally has an audio-filter unit.

## M4 message strategy

Do **not** transmit all 93 live-loop events. The visual engine needs the musical director's high-level intent, not every kick, hat or synth event.

Send only from the central control points:

1. At patch start: transport start, BPM, meter and a new session ID.
2. From `sp_clock`: one bar event per bar.
3. From `sp_scene`: scene ID and intensity.
4. From `sx_prod_macro_motion`: energy and cutoff macros once per bar.
5. On phrase boundaries: a phrase cue/index where useful.
6. At `sp_fin` / the `end` scene: transport stop and final cue.

This is a low message rate (roughly a few control packets per bar), avoids coupling visuals to the musical loop count, and preserves deterministic musical timing.

## Draft versioned OSC namespace

The proposed namespace is `/eli_lab/v1`. The exact argument order is to be frozen with the M4 protocol tests.

| OSC address | Arguments | Normalized event |
|---|---|---|
| `/eli_lab/v1/transport/start` | session ID, sequence, BPM, beats/bar | `transport.start` |
| `/eli_lab/v1/transport/stop` | session ID, sequence | `transport.stop` |
| `/eli_lab/v1/clock/bar` | session ID, sequence, bar index, BPM | `clock.bar` |
| `/eli_lab/v1/scene/select` | session ID, sequence, scene ID, intensity, bar index | `scene.select` |
| `/eli_lab/v1/scene/intensity` | session ID, sequence, intensity | `scene.intensity` |
| `/eli_lab/v1/macro/set` | session ID, sequence, macro name, normalized value | `macro.set` |
| `/eli_lab/v1/cue/trigger` | session ID, sequence, cue name | `cue.trigger` |
| `/eli_lab/v1/source/heartbeat` | session ID, sequence | `source.heartbeat` |

Every message should include a monotonically increasing sequence scoped to a unique session ID. A patch restart must use a new session ID so the receiver can distinguish a new run from a delayed/repeated packet in an old run.

Default to loopback (`127.0.0.1`) and a configurable dedicated AV Translation port. Remote-network listening should require deliberate configuration. OSC messages must validate against the registry and must never call arbitrary Python methods.

## Proposed visual interpretation

These are starting mapping ideas, not hard-coded rules:

- Scene ID + intensity select a visual scene profile (layout family, look, palette and generator mix).
- `energy` can drive a bounded combination of motion amount, particle density, layer FX mix or transition energy.
- `cutoff` can be mapped to a visual parameter such as detail, contrast or edge emphasis, but its destination should be user-selectable.
- Phrase cues can trigger quantized layout/look changes at a four-bar boundary.
- Bar events establish the transport phase and permit quantized visual changes.

The app must retain lock, hold, safety-range and manual-override precedence. Sonic Pi should not directly overwrite individual locked layers.

## Patch compatibility requirements for M4

- Keep the musical structure and sound-generation loops intact.
- Add a single small OSC helper and call it from the existing scene, clock, macro and end points.
- Use an explicit host/port; avoid relying on an implicit default receiver.
- Confirm the installed Sonic Pi version supports the chosen sender API.
- Keep OSC output optional so the patch still runs when AV Translation is closed.
- Provide a toggle or safe no-op path for rehearsal without the visual application.
- Test that OSC messages remain aligned with the patch's own scheduled clock.

## Current boundary

M3 owns the normalized control event/state contract and the audio analysis/modulation foundation. M4 owns the OSC receiver, session/heartbeat diagnostics, versioned protocol and modifications to the SONATA patch. The renderer remains unaware of OSC and Sonic Pi.
