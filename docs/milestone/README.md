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

AR1M0 completion is identified by immutable annotated tag `asr_r1_m0`; no
later AR1 tag exists. AR1M1 entered from that exact tag on 2026-09-01. Metadata
screening locks the User-directed five-row development order: Zipformer x-large
INT8, WeNet WenetSpeech streaming CTC INT8, Nemotron 3.5 Q8_0, Zipformer large
INT8, and WeNet AISHELL streaming CTC INT8. The order is not a score or ranking.
PengChengStarling is stopped by User decision because its 1.22 GB inference
closure exceeds the approximately 1 GB ASR budget.

All five exact rows have completed non-formal development bring-up in an
x86_64 Ubuntu 24.04 virtual environment limited to 2 vCPUs and CPU-only
execution. Native and thin-adapter paths produced partials and non-empty finals;
the lifecycle, offline, TTFT/full-utterance RTF, resource, timeout, cleanup, and
diagnostic post-process interface scaffolds are implemented. These are
development diagnostics from a changing worktree, not reviewed evidence, not
Pi 5 results, and not formal scores or qualification decisions.

The non-formal workstation baseline method uses a 1,000,000,000-byte RSS
reference with the existing 2.66-second controlled smoke identity. RSS is an
observation, not an automatic termination or elimination rule. The exact source
WAV has been recovered from controlled historical storage and its p0 crop has
been reproduced with the frozen checksum. Reviewed execution evidence still
requires the revised packet at a clean full SHA.

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
  Nemotron Q8_0 is 741,548,352 bytes; both require explicit RSS observation,
  but exceeding the 1 GB reference does not stop their POC work.
- Nemotron lists broad-coverage `zh-CN`, not `zh-TW`; M1 smoke cannot establish
  Taiwan Mandarin quality.
- The controlled source WAV and reproducible frozen p0 derivation are available;
  the revised method still needs a clean probe SHA before real acquisition.
- Workstation/aarch64 paths are documented, but Pi 5 behavior remains unproven.

## Next authorized work

Complete review of the M1 development segment, commit a clean candidate SHA,
and repeat the critical five-row workstation packet with the exact external
artifact closure. Close the documented fixture coverage gaps before M1 exit,
then repeat the frozen critical smoke and lifecycle cases on a real Pi 5 at the
same immutable SHA. Preserve all rows above the RSS reference and all failed
evidence. Do not publish a formal score, ranking, qualification, or Pi
disposition from the x86 workstation results.
