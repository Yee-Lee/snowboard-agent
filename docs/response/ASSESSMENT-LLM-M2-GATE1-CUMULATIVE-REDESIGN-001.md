# ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001

- **Date**: 2026-08-26
- **From**: LLM POC Technical Lead
- **To**: User; after approval, Core Designer
- **Status**: `R2 REVIEW APPROVED / USER REVIEW CONDITION SATISFIED / READY TO PUBLISH`
- **Replacement Gate 1 packet**: `G1-PI-COMPAT-007`
- **Superseded future-execution packet**: `G1-PI-COMPAT-006`

## Decision

P1～P12 become a cumulative Gate 1 + Gate 2 acceptance matrix. Passing evidence is produced once
and is not repeated merely because the external gate changes. Gate 1 now answers the two requested
questions with formal credit:

1. **LLM stability**: M4B-P10A on the physical Pi.
2. **Core integration feasibility**: M4B-P1, P6 and P7, supported by P11 provenance and P12 offline
   execution evidence.

Gate 2A executes only the remaining P2, P3, P4, P5 and P8 for Gate 1 finalists. Gate 2B executes P9
and P10B. A final Gate 2 decision combines the accepted evidence manifest chain rather than rerunning
already accepted work.

## Cumulative matrix

| Stage | Formal items executed | Formal items explicitly not repeated |
| --- | --- | --- |
| Gate 1 | P1, P6, P7, P10A, P11, P12 | none; first formal Pi evidence |
| Gate 2A | P2, P3, P4, P5, P8 | P1, P6, P7, P10A, P11, P12 |
| Gate 2B | P9, P10B and only change-affected regression | all unchanged accepted 1/2A items |

Carry-forward is valid when the Gate 1 Git commit is a trusted ancestor, its execution-surface lock
digest matches, and the runtime/model/config/protocol/fixture, Pi 5 4GB, OS, `swap=0`, offline and
evidence-manifest identities relevant to the accepted item match. A later evidence, ACK, delivery or
milestone-documentation commit changes `HEAD` but not the accepted execution surface. A changed
execution artifact invalidates only affected evidence. A later combined-run environment observation
may be repeated without relabelling it as a rerun of the accepted P item.

## Test-value and cost review

| Work | Value | Cost / duplication finding | Cumulative disposition |
| --- | --- | --- | --- |
| Provenance/license/exact identities | Prevents testing the wrong candidate | One review | P11 in Gate 1 |
| Offline wheel install/import/ELF/linkage | Proves deployability on product aarch64 | One clean install | P11 in Gate 1 |
| Model SHA-256 | Proves artifact and transfer integrity | One 1.6–2.6 GB read | Once before READY; receipt reused |
| READY/PING/JSONL/shutdown/orphan | Core process protocol | Normal lifecycle | P1 in Gate 1 |
| Cooperative cancel | Preferred operation stop | One observation | P6 in Gate 1; conditional only with P7 PASS |
| TERM/KILL/waitpid/rebuild/fatal outcome | Required Core fallback | One fault/rebuild cycle | P7 in Gate 1 |
| 20-session memory/thermal stability | Direct LLM stability | 20 generations + fixed cadence | P10A in Gate 1; never repeated in 2A |
| Offline pre/post target proof | Product requirement | Two host observations | P12 in Gate 1 |
| 20-case × 3 output/fallback sweep | Product quality, not candidate stability | At least 60 generations | P2/P3 in Gate 2A only |
| Cold/hot percentile benchmark | Selection/performance decision | Multiple loads + hot samples | P4 in Gate 2A only |
| Exact 15-second extreme timeout | Formal timeout semantics | Predeclared continuous 512-token chunks under one outer timer + rebuild | P5 in Gate 2A only; never workstation |
| Five-turn semantic isolation | Product conversation correctness | Extra semantic fixtures | P8 in Gate 2A only |
| Audio+LLM residency/combined soak | Final integration | Requires accepted Audio package | P9/P10B in Gate 2B only |
| Full-file hashes inside every child | No new evidence if metadata is unchanged | Dominates READY and allocates large memory | Removed |
| Repeating accepted P items after a gate transition | No new evidence with identical identity | Pure gate-boundary rework | Prohibited by cumulative matrix |

## Gate 1 optimized execution

Per candidate, the runner performs one model hash, then three purposeful Engine lifecycles:

1. **Normal lifecycle**: exact READY within the formal 10-second P1 deadline after hashing has
   completed; PING/PONG; twenty fixed single-turn sessions in one resident Engine; clean shutdown.
   Those same sessions are the P10A sample set, so there is no separate stability loop.
2. **Fault lifecycle**: start one fixed generation, observe the generation worker, issue CANCEL and
   measure 500 ms. Whether native cancel succeeds or requires escalation, execute exactly one P7
   force-abort path and prove waitpid/process-group absence.
3. **Recovery lifecycle**: rebuild from the unchanged receipt, require READY/PONG, complete one
   recovery generation, clean shutdown and prove orphan zero. Execute the deterministic fatal-outcome
   mapping without pretending to restart the product service.

P10A records all twenty sessions, five-second cadence, schema/terminal status, PSS/RSS, system-used
memory, threads, CPU, temperature and throttling; it applies the frozen slope and median rules. P11
and P12 reuse the packet pre/post work rather than rerunning provenance or network checks per child.

## `006` disposition and approval boundary

`G1-PI-COMPAT-006-20260826T125959Z-001` remains immutable evidence of a packet implementation
defect: its 10-second READY clock included a full model SHA pass. It is not candidate incompatibility
evidence and supplies no P credit. `007` moves the single streaming hash before READY timing.

The User authorized the cumulative model but requires reviewer approval of the validation design
before any execution. After that approval, one delivery will ask Core simultaneously to accept this
boundary and acknowledge the exact `007` source SHA; no separate contract-edit round is required.
Candidate results and finalist proposals still require User review before release.

## Reviewer finding revision

The latest independent review, `REVIEW-LLM-M2-CUMULATIVE-REDESIGN-001`, returned two blocking
findings. This revision addresses both without executing a model:

1. **Recursive Git invalidation removed**: the Gate 1 receipt now carries both chronological
   `execution_sha` and `execution_surface_sha256`. Gate 2A requires the former to be an ancestor and
   the latter plus component identities to match. Committing evidence or ACK documents therefore
   cannot force a Gate 1 rerun.
2. **Fast-model P5 trap removed**: P5 now uses the predeclared
   `M4B-P5-CONTINUOUS-TIMEOUT-002` outer operation. A completed 512-token chunk continues immediately
   under the original timer and never returns `RESULT`; the 15-second timeout, cancellation, READY,
   rebuild and cleanup paths are always exercised without post-result fixture adaptation.

The Reviewer approved both corrections in `ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE`. The User then
reported that approval in the active execution thread, satisfying the pre-execution review condition.
The remaining ordering requirement is to publish the reviewed source and bind its exact SHA before
starting the Pi command.

Reviewed execution source: `b5690bbbef50ce37af356fd29b88ab920207c38e`; execution-surface
SHA-256: `480adb939a6bfc359dfc2a10c9d478cece94df8fd24f8c48bb810d902e06d8d2`.
