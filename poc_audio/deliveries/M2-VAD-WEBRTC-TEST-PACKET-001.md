# M2-VAD-WEBRTC-TEST-PACKET-001

Status: `FROZEN / AUTHORIZED / NOT YET EXECUTED`

## Delivery contribution

This packet closes `FND-M2-001` only if exact WebRTC VAD 2.0.10 produces a
reviewable bounded scorecard on the M1 frozen 100-item fixture set. It does not
start M3, alter Audio HAL behavior, capture/play audio, or authorize parameter
tuning. Silero 6.2.1 remains conditional and may run only if the frozen trigger
below fires.

## Binding

| Field | Frozen value |
| --- | --- |
| Authority | `RESP-AUDIO-M2-GATE-REVIEW-001` |
| Primary | `vad-webrtc-2.0.10` |
| Source artifact | `webrtcvad-2.0.10.tar.gz`, 66,156 bytes, SHA-256 `f1bed2fb25b63fb7b1a55d64090c993c9c9167b28485ae0bcdd81cf6ede96aea` |
| Fixture set | M1 delivered Option A 100-item set: clear, pause, silence, noise, 25 each |
| Label index | SHA-256 `85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74` |
| Input | 16 kHz, mono, S16_LE, exact 20 ms / 320-sample frames |
| Candidate profile | WebRTC aggressiveness level 3 |
| Shared endpoint | First positive frame starts an event; 500 ms consecutive non-speech closes it at the last positive-frame end |
| Utterance padding | 300 ms before event start, 500 ms after event end; padding is reported separately and does not rewrite scored event boundaries |
| Repetition | One pass over 100 fixtures; no warm-up matrix, tuning, or alternate profile |
| Timeout | 10 minutes for the complete run |

## Frozen gates

- Speech-start recall `>=95%`, using the M1 `[-100,+300] ms` match window.
- Speech-end recall `>=90%`, using the M1 `[-200,+700] ms` match window.
- Start absolute boundary error p95 `<=300 ms`.
- End absolute boundary error p95 `<=700 ms`.
- Silence/noise false starts `<=1 per 10 evaluated non-speech minutes`.
- Final thread, file-descriptor and child-process state has zero delta/residue.
- Report clear, pause, silence and noise separately before aggregate results.

CPU, RTF and RSS are observations only. They do not reject WebRTC or activate
fallback. The fallback trigger is any frozen quality-gate failure, crash, OOM,
bounded timeout, or incomplete cleanup. No parameter change or rerun is allowed
after seeing WebRTC results.

## Controlled preparation and run

The source is acquired from the immutable manifest URL and must match the
frozen size/checksum before extraction. On the clean Pi exact candidate SHA:

```bash
python3 -m pip wheel --no-index --no-deps --no-build-isolation \
  --wheel-dir <new-controlled-wheel-dir> <controlled-source-tarball>
python3 -m venv --system-site-packages <new-controlled-runtime-dir>
<new-controlled-runtime-dir>/bin/python -m pip install \
  --no-index --no-deps <new-controlled-wheel>

timeout 600 bash poc_audio/tools/run_m2_vad_webrtc.sh \
  --runtime-python <new-controlled-runtime-dir>/bin/python \
  --runtime-wheel <new-controlled-wheel> \
  --source-artifact <controlled-source-tarball> \
  --fixture-dir <controlled-delivered-option-a-v1-dir> \
  --label-index <controlled-vad-labels-v1.json> \
  --output <new-controlled-result.json>
```

Before execution, record the full POC SHA, runtime wheel SHA-256, Pi platform,
temperature/throttle state, fixture-manifest SHA-256 and clean worktree. After
execution, record the result SHA-256, final temperature/throttle state and
independent process/audio-owner cleanup. Raw WAV and per-fixture controlled
results remain outside Git; only a sanitized reviewed scorecard may be added.

## Stop rule

- If WebRTC passes every frozen quality and cleanup gate, stop and submit it as
  the VAD M3 finalist recommendation. Do not execute Silero.
- If a frozen fallback trigger fires, preserve the WebRTC result unchanged and
  prepare the already-authorized exact Silero 6.2.1 row. Do not tune WebRTC.
- If artifact identity, fixture identity, environment, or evidence integrity is
  invalid, mark the run `INCONCLUSIVE` and stop; do not treat it as a Silero
  quality trigger.
