# ASR Product R1 Milestone Index

This file is the single source of truth for AR1 status.

Last updated: 2026-09-01

Overall reachability: `ON_TRACK`

Active milestone: `AR1M2 — Candidate Evaluation and Pipeline Selection (entry gates)`

The contract and receipt are committed on `asr_r1`. The legacy Audio tree is
isolated and recoverable at `audio_m4`. Candidate/control manifests, fixture
collection gates, minimal schemas, the fake runtime, unit tests, relative-path
enforcement, relocation verification, and data-safety checks complete AR1M0.
User approved its completion commit, annotated tag, and push on 2026-09-01.

AR1M0 and AR1M1 completion are identified by immutable annotated tags
`asr_r1_m0` and `asr_r1_m1`. AR1M1 entered from the M0 tag and completed on
2026-09-01. Metadata screening locked the User-directed five-row development
order: Zipformer x-large INT8, WeNet WenetSpeech streaming CTC INT8, Nemotron
3.5 Q8_0, Zipformer large INT8, and WeNet AISHELL streaming CTC INT8. The order
is not a score or ranking. PengChengStarling is stopped by User decision because
its 1.22 GB inference closure exceeds the approximately 1 GB ASR budget.

All five exact rows have completed non-formal development bring-up and clean-SHA
workstation repetition in an x86_64 Ubuntu 24.04 virtual environment limited to
2 vCPUs and CPU-only execution. Native and thin-adapter paths produced partials
and non-empty finals; the lifecycle, offline, TTFT/full-utterance RTF, resource,
timeout, cleanup, and diagnostic post-process interface scaffolds are
implemented. The User reviewed this scope and closed AR1M1 as workstation
development on 2026-09-01. These are non-formal development diagnostics, not
Pi 5 results, formal scores, or target-hardware qualification decisions.

The non-formal workstation baseline method uses a 1,000,000,000-byte RSS
reference with the existing 2.66-second controlled smoke identity. RSS is an
observation, not an automatic termination or elimination rule. The exact source
WAV has been recovered from controlled historical storage and its p0 crop has
been reproduced with the frozen checksum. Clean workstation execution SHAs and
the sanitized closeout are recorded.

| Milestone | Status | File |
| --- | --- | --- |
| AR1M0 | `COMPLETE` | [AR1M0](ar1_m0_research_readiness.md) |
| AR1M1 | `COMPLETE` | [AR1M1](ar1_m1_runtime_feasibility.md) |
| AR1M2 | `IN_PROGRESS — ENTRY GATES` | [AR1M2](ar1_m2_candidate_evaluation.md) |
| AR1M3 | `NOT_STARTED` | [AR1M3](ar1_m3_integrated_qualification.md) |
| AR1M4 | `NOT_STARTED` | [AR1M4](ar1_m4_outcome_handoff.md) |

## Fixture-set collection gates

| Gate | Required fixture work |
| --- | --- |
| AR1M0 | Freeze the audit and collection process only. Do not collect audio or assign fixture roles. |
| AR1M1 entry, before real smoke | Audit historical catalogs and select one authorized, frozen, approximately three-second PCM smoke fixture. Collect a replacement only if the audit proves no suitable fixture exists. |
| AR1M1 exit | Complete the metadata coverage matrix and document every gap and minimum closure action. No additional gap collection is required for M1 exit. |
| AR1M2 entry, before formal execution | Collect or derive only the minimum authorized prerecorded audio or annotations needed for documented gaps; finish references, checksums, sensitivity, license, controlled locators, and prior-use review; obtain User review and freeze disjoint development, adjustment, regression, and final-holdout manifests. |
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
  clean workstation probe SHAs are recorded.
- Workstation/aarch64 paths are documented, but Pi 5 behavior remains unproven.
- Intent taxonomy, English named entities, controlled volume, and speech-in-noise
  fixture gaps must close at AR1M2 entry before formal execution.

## Next authorized work

Complete the AR1M2 entry fixture gap closure and User-reviewed role freeze.
Prepare one immutable delivery SHA and repeat the critical smoke and lifecycle
cases on a real Pi 5 before formal scoring. No additional workstation model
rerun is pending unless implementation or measurement code changes or review
finds a defect. Preserve all rows above the RSS reference and all failed
evidence. Do not publish a formal score, ranking, qualification, or Pi
disposition from the x86 workstation results.
