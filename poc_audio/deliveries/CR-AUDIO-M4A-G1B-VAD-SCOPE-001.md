# CR-AUDIO-M4A-G1B-VAD-SCOPE-001 — VAD execution scope

- **Status**: `USER AUTHORIZATION RECORDED — CORE ACK / RECALL GATE PENDING — M2 VAD EXIT BLOCKED`
- **Raised**: 2026-08-18
- **Trigger**: `DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`
- **Core ACK commit**: `790c0f86e12422542ef94cacd3c4dd850e346bca`
- **Decision owners**: Core Designer and User
- **Architecture change**: `No`

## Trigger and affected delivery

Core Gate 1B authorizes only the SenseVoice ASR and Matcha TTS primary rows and
explicitly defers both VAD rows. This is valid for the focused M4a execution
budget, but the authoritative Audio POC final outcome still requires one approved
VAD, ASR and TTS baseline, or an evidence-backed no-go for a class. M2 cannot
execute a VAD candidate, produce a VAD finalist/no-go, or close its per-class exit
gate under the current scope.

This request does not block WP2 or the already-authorized ASR/TTS WP3 work. It
does block M2 completion and the final VAD delivery path.

## User-authorized strategy

The User decision is recorded in
[`RESP-AUDIO-M4A-G1B-VAD-SCOPE-001`](RESP-AUDIO-M4A-G1B-VAD-SCOPE-001.md):

1. `vad-webrtc-2.0.10` is the primary real-engine evaluation row.
2. `vad-silero-onnx-6.2.1` is a conditional fallback only after its exact
   Python 3.13/aarch64 `onnxruntime` closure and preflight are reviewed.
3. The faster-whisper bundled Silero profile is diagnostic context only and is
   not a formal candidate row.

This records the User side of the decision, not a finalist or winner. Core must
still ACK the exact rows/profile and close the missing aggregate start/end recall
gate before real candidate output is visible.

## Recommendation and interim rule

Obtain the committed Core ACK and freeze the WebRTC aggressiveness, shared
endpoint profile and aggregate start/end recall minimums before first load.
Until that response is directly delivered, do not build, install, import, load,
execute or benchmark either VAD row. Preserve `AT_RISK`; do not treat successful
ASR/TTS qualification as M2 completion or silently omit VAD from final delivery.
