# DELIVERY-015-PM-LLM-POC-CUMULATIVE-GATE-DESIGN

- **Date**: 2026-08-26
- **From**: LLM POC Team (M4b)
- **To**: User / Reviewer; after approval, Core Designer
- **Status**: `R2 REVIEW APPROVED / EXACT-SHA COMMIT PENDING / NOT DELIVERED`
- **Post-review exact source SHA**: `<PENDING-COMMIT>`
- **Replacement Gate 1 packet**: `G1-PI-COMPAT-007`
- **Defective historical attempt**: `G1-PI-COMPAT-006-20260826T125959Z-001`

## Requested design disposition

The User directed the POC to complete P1–P12 cumulatively across Gate 1 and Gate 2 instead of
rerunning the same accepted work at each external gate boundary:

| Stage | Formal execution |
| --- | --- |
| Gate 1 | P1, P6, P7, P10A, P11, P12 |
| Gate 2A | P2, P3, P4, P5, P8 |
| Gate 2B | P9, P10B and only change-affected regression |

An accepted item carries forward when its execution commit is an ancestor and its execution-surface
lock, runtime, model, config, protocol, fixture, Pi/environment and evidence-manifest identities
match. Later evidence/ACK/documentation commits do not invalidate it; execution drift invalidates
only the affected item. P5 remains physical-Pi-only and is not executed during design review.

## v6 correction

The v6 10-second READY clock incorrectly included a complete model SHA-256 pass. Its deadline
expirations are packet implementation defect evidence, not candidate incompatibility. The POC
withdraws the prior zero-finalist interpretation; v6 supplies no P credit and no candidate result.

v7 authenticates each read-only model once before child launch, records a metadata-bound receipt,
and starts the formal READY clock only at child launch. Rebuilds validate the small receipt/config/
schema identities and unchanged model metadata without rereading the model contents.

P5 uses a predeclared continuous-chunk outer request: a completed 512-token model chunk immediately
continues under the original 15-second timer and cannot emit an early `RESULT`. The timeout,
cancellation, READY health, rebuild and cleanup paths are therefore exercised even by a fast model,
without adaptive fixtures or a replacement-disposition round.

## Review and execution order

1. Independent reviewer checks the design packet, runner, schemas, lock, fixtures, failure semantics
   and pure unit/negative tests.
2. User accepts or rejects the reviewer finding.
3. Only after acceptance does the POC commit/push and replace `<PENDING-COMMIT>` with the exact SHA.
4. Core receives this delivery and returns one ACK covering the cumulative boundary, exact SHA and
   v6 supersession. User may separately authorize Pi execution before that ACK arrives.
5. Gate 1 cannot close and P credit cannot become final until the ACK binds the reviewed evidence
   manifest. Benchmark results and finalist proposals remain subject to User approval before release.

## Core ACK requested after reviewer approval

Core is asked to return one response that:

1. accepts the cumulative P-item allocation, ancestor provenance and execution-surface carry-forward
   rule, including documentation-only commits after Gate 1;
2. acknowledges the post-review exact source SHA and `G1-PI-COMPAT-007`;
3. records v6 as an implementation-defect attempt with no candidate disposition or P credit;
4. accepts explicitly User-authorized pre-ACK v7 evidence, while withholding final P credit and Gate
   closure until manifest review; and
5. confirms Gate 2A runs only P2/P3/P4/P5/P8 and Gate 2B runs P9/P10B when unchanged Gate 1 evidence
   remains valid.

This draft must not be copied into Core's handoff path until reviewer and User approval.
