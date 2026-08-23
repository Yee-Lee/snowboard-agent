# M2-VAD-METHOD-CORRECTION-RERUN-PACKET-001

Status: `DRAFT / USER EXECUTION AUTHORIZED / RESULT PUBLICATION PENDING`

## Purpose and authority

This is the single bounded recovery requested by the User after the original
WebRTC/Silero method was found not to represent the required product behavior.
It advances final-checklist VAD endpoint, pause, noise, reset, and reproducible
wrapper evidence. It does not close M2, start M3, or publish a candidate
disposition.

The method correction and invalid-result rationale are recorded in
[`CR-AUDIO-M2-VAD-METHOD-CORRECTION-001`](CR-AUDIO-M2-VAD-METHOD-CORRECTION-001.md).

## Fixed WebRTC recovery profile

| Field | Corrected value |
| --- | --- |
| Candidate | Exact WebRTC VAD 2.0.10 source/runtime identity already controlled |
| Fixtures | Same immutable 25 clear, 25 pause, 25 silence, and 25 noise WAV files |
| Input | 16 kHz mono S16_LE; 20 ms / 320-sample frames |
| Reset | Fresh engine and endpoint state for every independent WAV |
| Device startup | Do not feed or score the first 160 ms after fixture/device start |
| Engine profile | Aggressiveness level 3 |
| Onset debounce | Complete rolling 300 ms window; at least 14 of 15 frames voiced |
| Endpoint close | 500 ms consecutive non-speech; raw end is the final voiced-frame end |
| Capture padding | 500 ms before raw start; 600 ms after raw end |
| Pause semantics | One utterance envelope from first annotated start to final annotated end; an internal pause need not create a second endpoint |
| Coverage | Merge touching/overlapping padded intervals for coverage only |
| False activation | Count distinct endpoint activations in silence/noise after the startup mask |
| Repetition | One pass only; no mode, debounce, padding, threshold, or candidate matrix |

Start/end recall is based on whether padded capture retains the reference
utterance start/end. Complete-utterance coverage is reported separately. Raw
boundary error remains diagnostic because the User confirms that the human
labels intentionally include manual buffer. The existing 95%/90% recall and
one false activation per ten non-speech minutes remain visible gates under the
corrected semantics; raw boundary p95 is not used to reject the row pending
review of this method correction.

The confirmed impact/knock noise in `vad-noise-003` remains valid non-speech
risk. Only the device-start transient is masked.

## Execution

Use a clean Pi checkout at the exact new candidate SHA and the already
controlled WebRTC source, wheel, fixture directory, and label index:

```bash
timeout 600 bash poc_audio/tools/run_m2_vad_webrtc.sh \
  --runtime-python <controlled-webrtc-runtime-python> \
  --runtime-wheel <controlled-webrtc-wheel> \
  --source-artifact <controlled-webrtc-source> \
  --fixture-dir <controlled-delivered-option-a-v1> \
  --label-index <controlled-vad-labels-v1.json> \
  --output <new-controlled-draft-result.json>
```

Record exact SHA, clean worktree, input/result checksums, temperature/throttle,
and independent cleanup. The output status must remain
`DRAFT_*_USER_CONFIRMATION_PENDING`.

## Stop and publication rule

After WebRTC completes, stop and present aggregate plus per-fixture results to
the User. Do not commit/push a scorecard, update milestone disposition, submit
to Reviewer, or execute Silero based on the draft result until the User
explicitly confirms the result and next action.

If the User authorizes Silero after reviewing WebRTC, use the same corrected
utterance semantics and endpoint profile. Silero must prepend the official
64-sample context to each 512-sample model window and reset recurrent state and
context for every fixture.
