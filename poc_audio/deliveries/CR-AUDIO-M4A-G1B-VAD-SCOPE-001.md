# CR-AUDIO-M4A-G1B-VAD-SCOPE-001 — VAD execution scope

- **Status**: `REQUESTED — M2 VAD EXIT BLOCKED`
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

## Options

1. **Authorize exact WebRTC VAD fallback row before M2 exit (recommended).**
   Issue a new row-specific ACK for `vad-webrtc-2.0.10`; retain the frozen
   endpoint state machine, 20 ms/320-sample input and HAL-external boundary.
2. **Provide an already-approved exact VAD baseline.** Supply immutable artifact,
   license, wrapper, fixture and lifecycle evidence meeting the same frozen gate;
   receipt alone is not PASS and any new identity requires manifest intake.
3. **Revise the final Audio POC outcome.** Remove the VAD baseline/no-go
   requirement through an explicit contract and delivery-checklist change. This
   reduces final scope and is not recommended.

## Recommendation and interim rule

Choose Option 1 before M2 gate review. Until a committed decision is directly
delivered, do not build, install, import, load, execute or benchmark either VAD
row. Preserve `AT_RISK`; do not treat successful ASR/TTS qualification as M2
completion or silently omit VAD from the final delivery.
