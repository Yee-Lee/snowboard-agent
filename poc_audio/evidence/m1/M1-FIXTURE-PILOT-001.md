# M1-FIXTURE-PILOT-001 — Controlled Fixture Pilot

Status: `PASS`

## Delivery contribution

This evidence advances the final delivery checklist's controlled-fixture,
format/checksum, and data-safety requirements. It is an operational Pilot only
and does not permit VAD/ASR candidate advance or fixture-gate freezing.

## Baseline and method

- Source SHA: `519aec9ad65ddf6c47d25611d50291a8bb6ee209`
- Target: Raspberry Pi 5 with the reviewed native capture format: 48 kHz,
  stereo, S32_LE.
- The Pilot used a fresh controlled local collection revision; an earlier
  pre-recording remained separate and was not mixed with this 40-item set.
- The recorder verified each WAV's native metadata and SHA-256. The final
  manifest and raw audio remain Git-ignored on the controlled test system.

## Reviewed result

| Check | Result |
| --- | --- |
| Valid Pilot files | `PASS`, 40 / 40 |
| Clear speech | `PASS`, 10 clips |
| Natural pause | `PASS`, 10 clips |
| Silence | `PASS`, 10 clips; re-recorded after label review |
| Ambient noise | `PASS`, 10 clips |
| Non-speech observation | `PASS`, 240 seconds combined |
| Source SHA / manifest consistency | `PASS`, one full SHA |
| Audio device owner after collection | `PASS`, none |
| Representative human review | `PASS`, clear, pause, silence, and noise clips match their labels |

## Observations retained for later gates

- Human monitoring required a temporary +12 dB dual-mono copy with zero
  clipping. This transform is not part of the raw fixture, ASR candidate input,
  or Core AudioInput policy.
- Background noise is present and intentionally represented by the Pilot noise
  class. Formal review must retain the controlled noise labels and metadata.
- A perceptible sound when playback stops remains an M3 AudioOutput/TTS
  lifecycle risk; it does not invalidate this input-fixture Pilot.

## Gate decision

The operational Pilot is complete and reproducible. Formal completion still
requires the remaining 60 clips, 50 total ASR references, 600 seconds of
combined silence/noise, complete fixture review, and the independent Core
AudioInput change decision. M1 remains `CHANGE_REQUESTED / NOT FROZEN`.
