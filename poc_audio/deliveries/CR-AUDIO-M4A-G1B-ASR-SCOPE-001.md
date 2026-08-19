# Change request: Gate 1B ASR fallback scope after primary failure

- **Change request ID**: `CR-AUDIO-M4A-G1B-ASR-SCOPE-001`
- **Related ACK**: `DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`
- **Status**: `CHANGE_REQUESTED — CORE DECISION REQUIRED`
- **Decision owner**: Core Designer
- **POC owner**: Audio POC Technical Lead

## Trigger evidence

The only authorized ASR execution row,
`asr-sherpa-sensevoice-int8-2025-09-09`, completed all frozen full-fixture
repetitions at POC SHA
`63c2cc179bb3c2525201da0f7a78d2c50b63d759`. Reviewed evidence
[`M4A-G1B-WP3-FULL-QUALIFICATION-001`](../evidence/m2/M4A-G1B-WP3-FULL-QUALIFICATION-001.md)
records Taiwan-Mandarin core CER 41.629% against the <=20% hard gate and 6%
overall sentence correctness against the >=70% hard gate. All 20 hot cycles
reproduced one stable hypothesis hash per fixture, while latency, RTF, thermal
and cleanup completed normally.

SenseVoice is therefore rejected. The failure is retained; no normalization,
fixture, threshold, model, artifact or runtime parameter will be changed to
make the result pass.

## Delivery impact

Gate 1B currently leaves no authorized ASR row able to satisfy the M2 exit
condition. Without a new decision, the final checklist can deliver only an ASR
no-go, and M3 cannot begin ASR/HAL finalist qualification. VAD remains
independently blocked by `CR-AUDIO-M4A-G1B-VAD-SCOPE-001`.

## Requested decision

Choose one option in writing:

1. **Authorize the exact existing fallback row
   `asr-whispercpp-base-q5_1-1.9.2` for WP3 execution.** This is the recommended
   recovery path already anticipated by the Gate 1B ACK. A new row-level ACK
   must preserve its exact source/model hashes, two-thread CPU-only build,
   frozen `zh-TW` fixtures and current gates; provenance/notice review remains
   a final-reference blocker.
2. **Accept an evidence-backed ASR no-go.** M2 will close ASR with SenseVoice
   rejected and no finalist, preventing an approved VAD/ASR/TTS baseline but
   allowing an explicit no-go delivery.
3. **Provide another exact candidate identity.** This requires a new Gate 1B
   proposal/ACK and immutable artifact, dependency, license and aarch64/offline
   review before execution.

Until Core returns a new exact-row ACK, POC will not build, install, import,
load, execute or benchmark Whisper.cpp or any other deferred/rejected ASR row.
TTS-only remaining qualification may continue without implying ASR recovery or
M2 completion.
