# M1-NATIVE-AUDIO-001 — Native I2S Capability

狀態：`FAIL`
P1 native PCM capability：`FAIL`
P2 device/config evidence：`PASS`

## Baseline and method

- Corrected test SHA: `0edeb7d9f8ff3811d1480ab4b464db2842978233`
- Target: Raspberry Pi 5 Model B Rev 1.1, aarch64, Debian 13,
  kernel `6.12.47+rpt-rpi-2712`.
- Direct ALSA `hw:` capture was discarded to `/dev/null`; output probes played
  digital silence from `/dev/zero`. No raw audio was retained.
- The required environment pre-test passed at the same clean Pi SHA.
- Raw evidence remains in a Git-ignored local evidence directory.

An earlier run at SHA `f7826dc056bfda59a5b9ecb6dff887daa600bbcf`
is `INCONCLUSIVE`: its packet treated an ALSA exit code of zero as native rate
support even when ALSA warned that the requested rate was changed. The
corrected SHA records requested and actual rates and rejects coercion.

## Reviewed native matrix

| Direction | Requested format | Actual result |
| --- | --- | --- |
| Capture and playback | 48 kHz, 2 channels, S32_LE | `PASS`; exact native format |
| Capture and playback | 16 kHz or 44.1 kHz, 2 channels, S32_LE | `FAIL`; ALSA changed the actual rate to 48 kHz |
| Capture and playback | S16_LE or S24_LE | `FAIL`; device reports only S32_LE |
| Capture and playback | 1 channel | `FAIL`; native device reports 2 channels |

The direct hardware parameters for both directions report S32_LE, 2 channels,
and 48 kHz. Therefore the current 16 kHz, mono, S16_LE AudioInput target is not
a native capability of this driver/hardware configuration.

## Lifecycle and environment results

| Check | Result |
| --- | --- |
| Capture reopen at exact native format | `PASS`, 3/3 |
| Playback reopen at exact native format | `PASS`, 3/3 |
| Sequential different native rate | `UNAVAILABLE`; only 48 kHz is exact |
| Shared-clock concurrent capture/playback at 48 kHz stereo S32_LE | `PASS` |
| xrun/overrun/underrun text in accepted probes | none |
| Audio device owner after run | none (`PASS`) |
| Thermal throttling | none (`0x0`) |
| Temperature at start | 38.05 °C |

## P2 device/config record

- ALSA VoiceHAT capture and playback use the same direct device, `hw:0,0`.
- The boot audio configuration contains the `googlevoicehat-soundcard`
  overlay; its configuration SHA-256 is
  `28fa63909a5db2255dac7b7562f8ddcdce482ddfcc7e3aa80877692479bb9bd6`.
- The User/Designer confirmed INMP441 + MAX98357A wiring and power topology;
  `M1-HW-SMOKE-001` confirms manual capture/replay and speaker output.
- No endpoint, login account, private path, raw WAV, or private transcript is
  included in this evidence summary.

## Gate decision

P1 is `FAIL` under the accepted contract because native hardware cannot emit
16 kHz, mono, S16_LE. Do not relax or hide this condition with `plughw:`.
Proceed through `CR-AUDIO-M3-PCM-001` before Core M3 claims AudioInput contract
acceptance. P2 is `PASS` and does not require another manual smoke run.
