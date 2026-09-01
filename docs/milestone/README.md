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
AR1M1 entered from that exact tag on 2026-09-01. Its first authorized work is
metadata-only identity/runtime screening and fixture audit; real acquisition or
execution still requires an exact row, frozen packet, and clean candidate SHA.

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

- Exact PengChengStarling and WeNet identities remain AR1M1 lock items.
- Fixtures still require the planned prior-use and coverage audit before role
  assignment.
- Official aarch64/Pi compatibility is unproven.

## Next authorized work

Run metadata-only official-source screening for each candidate/runtime and audit
the historical fixture catalogs. Lock or stop each exact row before acquiring
artifacts. Do not build, import, load, or execute a real candidate until its
exact manifest, frozen smoke fixture, clean SHA, dependency closure, and
reviewed packet are recorded.
