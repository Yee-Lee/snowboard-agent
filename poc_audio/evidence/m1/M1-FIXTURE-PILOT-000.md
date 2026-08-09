# M1-FIXTURE-PILOT-000 — Native Pre-recording Audibility

Status: `INCONCLUSIVE`

## Purpose

This is the first authorized Pilot pre-recording. It checks whether a native
mic capture is intelligible when replayed before collecting the remaining
fixtures. It is not VAD/ASR candidate evidence.

## Baseline and method

- Source SHA: `a799d0d2b52c466b0a48bb2528383b00b1e0900e`
- One six-second clear-speech capture used the authorized direct native format:
  48 kHz, stereo, S32_LE.
- The operator replayed the local WAV and reported that volume was too low to
  hear reliably.
- Read-only PCM inspection reported only format and per-channel level; the WAV
  was not copied, transformed, or committed.

## Reviewed result

| Check | Result |
| --- | --- |
| Native WAV format and duration | `PASS`, 48 kHz, stereo, S32_LE, 6.000 seconds |
| Capture channel 0 | `PASS`, peak `-15.0 dBFS`, RMS `-29.2 dBFS` |
| Capture channel 1 | `PASS / EXPECTED SILENCE`, peak/RMS `-186.6 dBFS` |
| Operator replay audibility | `FAIL`, nearly inaudible |
| Audio device owner after analysis | `PASS`, none |

## Finding and required follow-up

The `demo_audio` wiring reference confirms that the INMP441 `L/R` selection
pin is tied to GND, selecting the left I2S channel. Therefore the observed
single active channel is expected and does not indicate a mic wiring fault.
The microphone signal is present at a usable level on that channel, so this is
not evidence of global capture failure.

The operator's low-volume replay is a real observation, but the available
evidence does not yet distinguish output routing, output gain, and the need
for a separate monitoring transform. The Pilot is `INCONCLUSIVE`; do not
record the remaining items yet.

Next, perform a controlled local-only monitoring diagnostic that leaves the
native source immutable: compare the original stereo file with a temporary
unity-gain version that duplicates the active channel to both playback
channels. If it is audible, record an explicit monitoring channel policy. If
it remains quiet, inspect output routing/gain independently before continuing.
This diagnostic does not change the future ASR conversion boundary, which must
remain aligned with Core AudioInput Option A.
