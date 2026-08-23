# RESP-AUDIO-M4A-G1B-VAD-SCOPE-001 — VAD candidate strategy

Date: `2026-08-23`

Status: `USER AUTHORIZATION RECORDED / CORE ACK AND RECALL GATE PENDING / EXECUTION NOT YET AUTHORIZED`

## User decision

The User authorizes the following exact M2 strategy, subject to a committed Core
ACK and completion of the pre-result control items below:

1. **Primary evaluation row — `vad-webrtc-2.0.10`.** Use the PyPI source
   distribution with SHA-256
   `f1bed2fb25b63fb7b1a55d64090c993c9c9167b28485ae0bcdd81cf6ede96aea`
   and size 66,156 bytes. It is the first real-engine row to qualify.
2. **Conditional fallback — `vad-silero-onnx-6.2.1`.** Its source commit is
   `7e30209a3e901f9842f81b225f3e93d8199902b1`; the exact ONNX SHA-256 is
   `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.
   It becomes execution-eligible only after the Python 3.13/aarch64
   `onnxruntime` wheel and complete transitive closure, provenance, license and
   offline preflight are immutable and reviewed.
3. **Historical diagnostic only — faster-whisper bundled Silero VAD v6.** The
   previously observed faster-whisper pipeline used its bundled Silero ONNX in
   addition to an upstream recorder endpoint. That result may guide diagnostic
   comparison, but it is a distinct artifact and two-stage pipeline. It cannot
   enter the formal scorecard, establish causality or replace either exact row.

This decision authorizes a primary/fallback evaluation path, not a winner. The
M2 result can propose a provisional finalist only after comparable isolated
evidence is reviewed. M3 then qualifies an already-authorized M2 finalist on
the real microphone and pinned Audio HAL; it does not introduce a new engine.
M4 retains the combined-session, offline and failure-path gates before final
acceptance.

## Frozen shared boundary

- Input at the POC boundary remains 16 kHz, mono, S16_LE, exactly 20 ms / 320
  samples. Candidate-specific buffering may not resample or alter HAL behavior.
- Both formal rows use the same external, separately versioned endpoint state
  machine. Frame/model observation and utterance endpoint policy remain
  separately reported.
- Fixtures, fixture checksums, endpoint/padding policy, warm-up, repetition,
  bounded timeout, cleanup proof and reporting schema must be identical unless
  an immutable backend requirement is explicitly recorded.
- WebRTC aggressiveness and every endpoint parameter must be committed before
  first load. No parameter may be selected or changed after candidate results
  are visible.
- Real VAD remains outside the Audio HAL and product composition root.

The frozen VAD definitions in `poc_audio/fixtures/metrics_v1.md` remain in
force: start match window `[-100 ms, +300 ms]`, end match window
`[-200 ms, +700 ms]`, absolute start/end p95 limits `300/700 ms`, and at most
one silence/noise false start per ten evaluated non-speech minutes. Clear,
pause, silence and noise results must be reported separately before aggregate
results.

## Open pre-result gate

The frozen metric document requires recall reporting but does not state an
aggregate speech-start or speech-end recall minimum. The earlier M1 draft
proposed start recall >=95% and end recall >=90%, but explicitly labelled those
values as awaiting approval. Core/User must either adopt those exact values or
commit replacement values before any real candidate result is disclosed. This
is a gate clarification, not permission to tune after results.

Core ACK must also confirm the two-row disposition, the exact WebRTC profile
(including aggressiveness), the shared endpoint profile and the Silero
eligibility condition. Until that committed ACK and the recall gate exist, do
not build, install, import, load, execute or benchmark either real VAD row.

## Requested Core disposition

Please return one committed response that:

- accepts `vad-webrtc-2.0.10` as the primary M2 row;
- accepts `vad-silero-onnx-6.2.1` as the conditional fallback under the stated
  runtime-closure rule;
- freezes the WebRTC/endpoint profile and aggregate start/end recall gates
  before execution; or
- records exact modifications and keeps the execution hold in force.

M2 remains `AT_RISK` and cannot pass its VAD exit gate from this User decision
alone. An evidence-backed no-go remains valid if the authorized rows later fail
the frozen gates or cannot close provenance/runtime eligibility.
