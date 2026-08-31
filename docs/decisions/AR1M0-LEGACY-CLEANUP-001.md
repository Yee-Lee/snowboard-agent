# AR1M0 Legacy Cleanup Decision

- **Status**: `USER AUTHORIZED / EXECUTED ON ASR_R1`
- **Date**: 2026-08-31
- **Recovery point**: `audio_m4` /
  `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`

User authorized direct removal of the legacy Audio M0-M4 active tree from
branch `asr_r1`. Git ancestry is retained, so every removed file remains
recoverable from `audio_m4`.

The R1 contract and receipt moved into `docs/handoff/`. Old TTS, P9, M3 HAL,
combined pipeline, candidate matrices, evidence, packets, runners, tests, and
documents are not AR1 inputs. Any reused fact, fixture identity, or code idea
must receive a new AR1 manifest or implementation with an explicit `audio_m4`
reference.

This cleanup does not complete AR1M0, authorize model execution, or create a
milestone tag.
