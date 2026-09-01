# ASR Product R1 Milestone Index

This file is the single source of truth for AR1 status.

Last updated: 2026-09-01

Overall reachability: `ON_TRACK`

Active milestone: `AR1M1 — Runtime Feasibility and Integration Readiness`

The contract and receipt are committed on `asr_r1`. The legacy Audio tree is
isolated and recoverable at `audio_m4`. Candidate/control manifests, fixture
collection gates, minimal schemas, the fake runtime, unit tests, relative-path
enforcement, relocation verification, and data-safety checks complete AR1M0.
User approved its completion commit, annotated tag, and push on 2026-09-01.

No real model acquisition, build, or execution occurred. AR1M0 completion is
identified by immutable annotated tag `asr_r1_m0`; no later AR1 tag exists.
AR1M1 entered from that exact tag on 2026-09-01. Metadata screening now locks
the User-directed five-row development order: Zipformer x-large INT8, WeNet
WenetSpeech streaming CTC INT8, Nemotron 3.5 Q8_0, Zipformer large INT8, and
WeNet AISHELL streaming CTC INT8. The order is not a score or ranking.
PengChengStarling is stopped by User decision because its 1.22 GB inference
closure exceeds the approximately 1 GB ASR budget.

The non-formal workstation baseline method is frozen at a 1,000,000,000-byte
sampled process-tree RSS ceiling with the existing 2.66-second controlled smoke
identity. Real acquisition and execution remain blocked until that external WAV
is restored, passes checksum/PCM preflight, and the probe packet has a clean
full SHA.

| Milestone | Status | File |
| --- | --- | --- |
| AR1M0 | `COMPLETE` | [AR1M0](ar1_m0_research_readiness.md) |
| AR1M1 | `IN_PROGRESS` | [AR1M1](ar1_m1_runtime_feasibility.md) |
| AR1M2 | `NOT_STARTED` | [AR1M2](ar1_m2_candidate_evaluation.md) |
| AR1M3 | `NOT_STARTED` | [AR1M3](ar1_m3_integrated_qualification.md) |
| AR1M4 | `NOT_STARTED` | [AR1M4](ar1_m4_outcome_handoff.md) |

## Fixture-set collection gates

| Gate | Required fixture work |
| --- | --- |
| AR1M0 | Freeze the audit and collection process only. Do not collect audio or assign fixture roles. |
| AR1M1 entry, before real smoke | Audit historical catalogs and select one authorized, frozen, approximately three-second PCM smoke fixture. Collect a replacement only if the audit proves no suitable fixture exists. |
| AR1M1 exit / AR1M2 entry | Complete the coverage matrix; collect only the minimum authorized prerecorded audio or annotations needed for documented gaps; finish references, checksums, sensitivity, license, and prior-use review. |
| Before AR1M2A formal execution | Obtain User review for every holdout proposal and freeze disjoint development, adjustment, regression, and final-holdout manifests. |
| AR1M3 entry, after pipeline freeze | Using frozen prompts and capture procedure, collect Pi 5 target-microphone qualification sessions. These sessions cannot be used for tuning or AR1M2 selection. |

No result may be used to retroactively move a fixture between roles. A newly
discovered coverage gap stops the affected formal run and requires a reviewed
method revision and new frozen packet before collection or restart.

## Risks

- Zipformer x-large has approximately 736 MiB of declared inference files and
  Nemotron Q8_0 is 741,548,352 bytes; both are memory-capped smoke candidates,
  not established 1 GB fits.
- Nemotron lists broad-coverage `zh-CN`, not `zh-TW`; M1 smoke cannot establish
  Taiwan Mandarin quality.
- The frozen controlled smoke WAV is not present in known local controlled
  storage, so no real artifact acquisition or execution may begin.
- Workstation/aarch64 paths are documented, but Pi 5 behavior remains unproven.

## Next authorized work

Restore the checksum-bound external smoke WAV and pass fixture preflight. At a
clean packet SHA, acquire and verify each exact artifact outside Git, then run
the five non-formal workstation smokes in the frozen order. Record warm decode
RTF, load time when exposed, and peak process-tree RSS; stop any row exceeding
1,000,000,000 bytes. Do not publish a formal score, ranking, qualification, or
Pi disposition from these workstation results.
