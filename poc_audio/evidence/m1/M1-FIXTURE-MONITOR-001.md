# M1-FIXTURE-MONITOR-001 — Temporary Monitoring Gain

Status: `PASS`

## Purpose

Resolve the pre-recording audibility observation without changing the
authorized native fixture source. This is a local monitoring diagnostic, not a
gain decision for ASR fixtures or the Core AudioInput HAL.

## Baseline and method

- Source SHA: `fbb19acc6b5d67008c4b504f26f38df222ae1978`
- The authorized native source from `M1-FIXTURE-PILOT-000` remains immutable.
- A Git-ignored temporary WAV selected native channel 0, duplicated it to both
  playback channels, and applied saturating `+12 dB` gain only for monitoring.
- The tool reported `0` clipped source samples; the operator replayed the
  derived WAV and confirmed it was clear and not distorted.

## Reviewed result

| Check | Result |
| --- | --- |
| Monitoring audibility | `PASS`, operator confirmed clear playback |
| Temporary gain | `PASS`, +12 dB with saturation protection |
| Clipped source samples | `PASS`, 0 |
| Original native WAV | `PASS`, not modified |
| Raw/derived audio in Git | `PASS`, none |

## Observations retained for later gates

- Background noise is audible. It is non-blocking for Pilot recording and must
  be represented by the planned controlled noise fixtures during Formal review.
- A perceptible noise/cut occurs when playback stops. This is not evidence of
  ASR capture failure; treat it as an `M3 AudioOutput` stop/transient risk to
  test with TTS and HAL lifecycle evidence.

## Gate decision

Pilot collection may resume using immutable native raw capture. The +12 dB
transform is permitted only for local human monitoring and must not be silently
applied to candidate input, fixture checksums, or the Core HAL contract.
