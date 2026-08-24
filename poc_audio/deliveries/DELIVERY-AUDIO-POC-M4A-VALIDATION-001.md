# DELIVERY-AUDIO-POC-M4A-VALIDATION-001

**Date**: 2026-08-24  
**From**: Audio POC Team  
**To**: Core Designer  
**Status**: `READY FOR CORE GATE 2A SELECTION ACK`

## Complete return identity

This is the single M3/Gate 2A return. The immutable reviewed evidence commit is
`54a06dcca373ffe5c8d405b613b390425ca34faa` on branch `audio`. It contains the
User-approved review, milestone state and Core packet ACK-003 intake.

| Field | Exact identity |
| --- | --- |
| Audio execution SHA | `f7b9694d1477f26513880526e0718d2b3c5766b3` |
| Core HAL execution SHA | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Core HAL acceptance SHA | `3cbefc58ee1b415c5a0a232cc4ce1606b7146e55` |
| Core packet ACK commit | `cae21217b2f7d812511bde77edb2cd1eb65e8f06` |
| Packet manifest SHA-256 | `64efb3bf3299ad8d017914f307d70dedd8a4bcf88d74e23a87911fcf0ddb65f3` |
| Final review | `poc_audio/evidence/m3/M3-RISK-FOCUSED-QUALIFICATION-REVIEW-001.md` |
| Machine manifest | `poc_audio/evidence/m3/M3-RISK-FOCUSED-QUALIFICATION-001/manifest.json` |
| Sanitized 22-result summary | `poc_audio/evidence/m3/M3-RISK-FOCUSED-QUALIFICATION-001/summary.sanitized.json`; SHA-256 `1fc128545b645f1edfe696dab4d6544723eacdf47c9fe11a8e0d8bfc18760594` |
| Controlled session | `controlled://audio-m3/20260824-r3` |

The final result set contains 22 unique test IDs, one Audio/Core identity and no
selected failure: `18 PASS / 0 FAIL / 4 human-review INCONCLUSIVE`. The four
machine-INCONCLUSIVE rows are VAD, direct ASR, HAL ASR and TTS, whose packet-defined
human review is complete. User approved their reviewed `PASS` publication on
2026-08-24. Rejected attempts remain append-only and are not in the selected set.

## M4A P1–P12 decision table

| ID | Reviewed result | Evidence and boundary |
| --- | --- | --- |
| M4A-P1 | `PASS` | Core HAL produces exact 16 kHz mono S16_LE, 320-sample/640-byte/20 ms frames; ASR layer does not resample. |
| M4A-P2 | `PASS` | Base Q8 produced non-empty text for all five final target-mic fixtures on direct and HAL/VAD paths. |
| M4A-P3 | `PASS` | 60 s silence produced zero VAD event; speech was non-empty/no garble. Final HAL ASR p50/p95 latency was `1330.243/1366.650 ms`, peak RSS `284.500 MiB`; inherited Pi RTF p95 remains below `2.0`. |
| M4A-P4 | `PASS` | Matcha emits native 16 kHz mono S16_LE PCM. POC sends it unchanged to Core AudioOutput; pinned Core performs its accepted 48 kHz stereo S32_LE hardware adaptation. |
| M4A-P5 | `PASS` | Six ordered PCM sequences completed physical target-speaker playback through Core drain; no truncation or device residue. |
| M4A-P6 | `PASS` | User scored all six prompts `5/5`, median `5`, with no critical meaning-changing misread. |
| M4A-P7 | `PASS` | Accepted Pi ASR resource evidence is inherited; M3 final five-item target run observed p50/p95 `1333.591/1363.075 ms` direct, peak RSS `285.531 MiB`, no deadline/OOM/growth/cleanup/throttle blocker. |
| M4A-P8 | `PASS` | Accepted Matcha Pi evidence: first-buffer p95 `285.098 ms`, RTF p95 `0.112776`, peak RSS `227.531 MiB`, end temperature `49.05 °C`, `throttled=0x0`; M3 adds six target-speaker completions. |
| M4A-P9 | `CORE ACCEPTED / AUDIO INTEGRATION UNBLOCKED / NOT EXECUTED` | Versioned surrogate and corrected Core ACK `caf4f7ba867e4ebc1972df0ade86c605a873a286` are fixed. No P9 PASS or LLM credit is claimed; prior authority makes this non-blocking for Audio M3. |
| M4A-P10 | `PASS` | Start/stop, reopen ×5, invalid input/output, cancellation and force-abort are bounded; final child/thread/task/fd/stream/device-owner deltas are zero. |
| M4A-P11 | `PASS FOR INTERNAL GATE 2A / FINAL LEGAL OPEN` | Clean exact-SHA Pi checkouts and pinned artifacts reran offline. Matcha archive license/training lineage still blocks redistribution, product adoption and Gate 2B final-winner approval. |
| M4A-P12 | `PASS` | VAD, direct/HAL ASR, TTS and lifecycle candidate work ran inside an unprivileged network namespace with loopback down and no runtime fetch. |

## Gate 2A finalist recommendation

| Domain | Unique M4 finalist | Fixed identity / configuration |
| --- | --- | --- |
| VAD | Silero ONNX 6.2.1 | Model SHA-256 `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`; threshold `0.5/0.35`, 250 ms minimum, 160 ms startup mask, 500 ms close, 500/600 ms padding |
| ASR | whisper.cpp 1.9.2 base Q8 | `ggml-base-q8_0.bin` SHA-256 `c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9`; P0, four threads, `zh`, greedy, fixed prompt |
| TTS | sherpa-onnx 1.13.5 Matcha zh/en | Archive SHA-256 `271b804af570400d3bcdcb53bf6e53cc9f75180ee763b9f13eb5eaf2b0d086ef`; Vocos SHA-256 `b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e`; native 16 kHz mono S16_LE |

The small-Q8 fallback is not activated because no critical semantic failure or
category-wide paired regression occurred. M3.1 is not activated because target-mic
low-volume speech was retained and exact on both ASR paths without gain/pre-roll.

## Preserved findings and remaining scope

- Superseded packaging, overlapping PCM ownership and transient LIFE-03 results
  remain preserved; append-only recoveries close the selected paths without gate
  relaxation.
- Target product distance is `0.8–1.0 m`. Low absolute level remains an observation,
  not a qualified front-end blocker.
- After Core's mechanical ACK closes M3, Audio will execute the accepted P9 surrogate
  as internal M4 work, then run at least 20 combined VAD/ASR/TTS sessions, failure
  injection, combined resource/offline evidence and Gate 2B review.
- Gate 2A selection is not final reference, production lock or `POC Accepted`.
- Matcha legal lineage remains blocking for redistribution/product adoption/final
  winner approval, but not for this internal offline Gate 2A POC.

## Single Core action

Please issue one committed `RESP-AUDIO-POC-M4A-VALIDATION-001.md` with either:

1. `ACKNOWLEDGED — GATE 2A SELECTION ACCEPTED`, repeating the exact Audio evidence
   commit, Audio/Core execution SHAs, three M4 finalists, P9 boundary and remaining
   M4/legal limits; or
2. one response listing every exact identity or blocking evidence mismatch together.

No Core source change, new Pi execution, remote-branch validation, rescoring,
additional packet signoff or intermediate authorization is requested. After ACK,
Audio will mark M3 complete and separately plan M4; Core does not need to direct the
Audio execution sequence.
