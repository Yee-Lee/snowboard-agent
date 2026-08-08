# M1-HW-SMOKE-001 — Manual I2S Audio Smoke Check

狀態：`PARTIAL PASS`

## Purpose

Verify that the configured I2S microphone and speaker path is manually usable
before the native PCM capability test. This is diagnostic evidence only; it
does not close Core M3 conditions P1 or P2.

## Scope and source

- Diagnostic source: `demo_audio` `hw/audio/test` scripts.
- Exact script commit SHA: not recorded; this run is not a reproducible source
  baseline.
- Raw WAV files and complete terminal output remain outside Git.

## Reviewed observations

| Check | Result | Sanitized observation |
| --- | --- | --- |
| Speaker manual playback | `PASS` | The VoiceHAT ALSA playback card/device was selected through `plughw:`. The test reported 48 kHz, S16_LE, stereo and the operator confirmed the left/right prompts. The operator stopped the repeating prompt with Ctrl-C; the resulting interrupted-call messages are not xrun evidence. |
| Microphone manual capture and replay | `PASS` | The same ALSA capture card/device was selected through `plughw:`. Two 5-second recordings at 44.1 kHz, S16_LE, stereo completed, were locally amplified, and were replayed with operator-reported success. |
| Native PCM capability | `INCONCLUSIVE` | Neither diagnostic script uses `hw:` or proves the 16 kHz, mono, 20 ms input contract. |
| Lifecycle and cleanup | `INCONCLUSIVE` | The scripts do not prove start/stop/reopen, device owner cleanup, xrun behaviour, or a stable device/config baseline. |

## Required follow-up

1. Run a committed M1 test packet using `hw:` to collect the rate, channel and
   sample-format matrix for both input and output.
2. Attempt the 16 kHz, mono, S16_LE, 20 ms AudioInput contract and record the
   exact conversion location if it is unavailable natively.
3. Record ALSA identifier, driver/config hash, sequential reopen, xrun and
   device-owner cleanup evidence without storing endpoint, account, raw audio,
   or full private terminal output in Git.
