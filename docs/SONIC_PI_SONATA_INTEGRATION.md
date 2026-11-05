# SONATA Expanded — Sonic Pi / AV Translator Integration Notes

## Source inspected

Repository: [`ilyaminineli/sonicpi_eli_lab`](https://github.com/ilyaminineli/sonicpi_eli_lab)  
Patch: [`04_LIVE/SEULPIRLEAMBACY/SONATA_expanded.rb`](https://github.com/ilyaminineli/sonicpi_eli_lab/blob/main/04_LIVE/SEULPIRLEAMBACY/SONATA_expanded.rb)

The M4 sender is installed in the live patch at the musical control points only. It does not instrument the 93 synth/drum loops.

## Musical clock and form

- Tempo: **92 BPM**.
- Meter: **4 beats per bar**.
- Form: **384 bars**, approximately **16 minutes 42 seconds** at 92 BPM.
- Structure: **16 scene changes**, including the final `end` scene.
- The bar clock increments `sp_b_count`, cues `sp_b`, then sleeps for four beats.
- Scene changes update `sp_sc` and `sp_int`, then cue `sp_sc_change`.
- The synchronized macro loop updates `sx_m_e` (energy), `sx_m_c` (filter cutoff) and `sx_macro_phr` (phrase index).
- The local `F:` sample root remains Sonic Pi's responsibility; AV Translator does not index those samples.

## Stable scene IDs and intensities

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
| `end` | final marker | 0.00 |

`sp_b_count` increments before `sp_b` is cued, so OSC `bar_index` is **1-based**.

## Patch sender configuration

At the top of `SONATA_expanded.rb`, the helper exposes three values:

- `$sp_av_enabled = true` — set to `false` for an audio-only rehearsal.
- `$sp_av_host = "127.0.0.1"` — explicit AV Translator bind address.
- `$sp_av_port = 57121` — match the UDP port shown in the AUDIO / CONTROL dock.

A unique session identifier is generated at patch start from a wall-clock timestamp with a microsecond component; it does not depend on the patch's seeded musical random generator, so rapid restarts receive distinct IDs. A shared sequence counter increments for each outgoing message inside a short mutex-protected sender section, so concurrent musical loops cannot reuse or reorder sequence numbers. The helper uses Sonic Pi's `osc_send(host, port, path, *args)` API and does not depend on Sonic Pi's incoming OSC port. If AV Translator is closed, local UDP sends are harmless; the patch's audio structure and cues continue to run.

## Connect Sonic Pi from the AV Translator UI

1. Open the **AUDIO / CONTROL** dock.
2. Under **SONIC PI CONNECTION · OSC /eli_lab/v1**, leave **RECEIVER ADDRESS** at `127.0.0.1` and **UDP PORT** at `57121` when Sonic Pi and AV Translator run on the same computer.
3. Click **START OSC RECEIVER**. The status should change from `STOPPED` to `LISTENING`.
4. Click **COPY SONATA SETTINGS** and paste the two lines into the sender configuration at the top of `SONATA_expanded.rb`, or verify that the patch already has the same host and port.
5. Run `SONATA_expanded.rb` in Sonic Pi. The receiver should change to `LIVE`; received/accepted counts should increase and the active session ID should appear.
6. To test the receiver without starting Sonic Pi, run the local test sender shown below.

Sonic Pi is **not** an audio input device and will not appear in the audio-device dropdown. The OSC connection and audio capture are separate: use the OSC receiver for transport, scenes and macros; use an audio input or system loopback only when you also want live sound analysis.

For Sonic Pi on a different computer, bind the receiver to the AV Translator computer's reachable LAN IPv4 address (or a deliberate interface), set `$sp_av_host` to that same address, and allow inbound UDP on the selected port in the host firewall. Do not use `127.0.0.1` for a remote sender; loopback only reaches the machine on which the receiver is running.

## Version 1 wire protocol

Namespace: `/eli_lab/v1`. Every event begins with a string session ID and positive integer sequence number. Sequence numbers increase across all event types for one patch run. Restart the patch to generate a new session ID.

| Address | Arguments after session ID + sequence | Event |
|---|---|---|
| `/transport/start` | BPM (float), beats/bar (int) | `transport.start` |
| `/transport/stop` | none | `transport.stop` |
| `/transport/tempo` | BPM (float) | `transport.tempo` |
| `/clock/bar` | 1-based bar (int), BPM (float), beats/bar (int) | `clock.bar` |
| `/scene/select` | scene ID (string), intensity (float 0..1), bar (int; `0` only for the initial pre-clock scene marker, otherwise 1-based) | `scene.select` |
| `/scene/intensity` | intensity (float 0..1) | `scene.intensity` |
| `/macro/set` | name (`energy` or `cutoff`), value (float 0..1) | `macro.set` |
| `/cue/trigger` | cue name (identifier) | `cue.trigger` |
| `/source/heartbeat` | none | `source.heartbeat` |

The initial `in` scene is announced before the first clock tick and therefore carries `bar_index=0` as a pre-clock marker; the first `/clock/bar` is bar 1. Every subsequent scene event is emitted after the preceding scene's bar-counted form block and carries the current 1-based bar index. The cutoff normalization is `clamp((sx_m_c - 48.0) / 70.0, 0.0, 1.0)`. Energy is already normalized in the patch. Macro messages are sent once per bar; a phrase cue is sent on four-bar boundaries. Bar messages are emitted once per bar, and a separate heartbeat is sent every four bars. The application treats SONATA as clock authority, disables its internal test clock on `transport/start` or, as a packet-loss fallback, the first accepted `clock/bar`, and derives the M3 `transport.phase` modulation source from the most recent bar clock. Macro values feed the existing M3 modulation matrix, including its smoothing, hold, lock, manual-override and intensity-ceiling behavior.

## Receiver safety and application threading

- Default bind is loopback; binding to another interface is an explicit user choice.
- Only known versioned addresses, exact argument counts, strict OSC types, registered macro names and safe numeric ranges are accepted.
- Session IDs are retained in a bounded 64-session replay history and cannot be reused within that window. Packets from a superseded session and duplicate/out-of-order sequences are rejected.
- Input is rate-limited (60 messages/second by default) and the M3 event queue remains bounded.
- The receiver runs on one dedicated daemon worker. It only creates validated `ControlEvent` objects and submits them to the queue.
- The main application tick drains a bounded number of events, updates performance-control state and applies modulation. Qt widgets, composition state and OpenGL resources are never touched by the OSC worker.
- The AUDIO / CONTROL dock shows listening/live/stale status, last address, active session, accepted/rejected/dropped counts and last packet age.

A lost packet does not block the clock: the next bar or macro packet is handled independently. Malformed datagrams are discarded and counted; the receiver remains available. A stale sender is recovered by restarting SONATA with a fresh session ID. If the receiver itself was stopped, restart it before restarting the patch.

## Test without Sonic Pi

With AV Translator running and OSC started on loopback port 57121:

    python scripts/osc_test_sender.py --host 127.0.0.1 --port 57121

The script sends start, bar, scene, energy/cutoff, heartbeat, phrase and end events. Protocol and local UDP receiver tests run in CI without Sonic Pi or audio hardware.

## Live rehearsal checklist

1. Start AV Translator and enable the OSC receiver on `127.0.0.1:57121`.
2. In Sonic Pi, leave `$sp_av_enabled = true`, verify host and port, then run SONATA.
3. Confirm BPM 92, bar positions 1 through 384, all 16 scene IDs, energy/cutoff movement, four-bar phrase cues and final stop.
4. Stop/restart the patch and confirm the new session is accepted while delayed packets from the prior session are rejected.
5. Stop AV Translator's receiver, confirm SONATA audio continues, then restart the receiver and restart SONATA.

**Validation boundary:** protocol, sender insertion and receiver tests are implemented. The complete 384-bar performance has not been executed inside Sonic Pi in CI; timing and machine-specific rehearsal remain a manual sign-off.
