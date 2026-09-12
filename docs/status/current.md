# Current handoff

- Updated: 2026-09-12
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B cognition/product development rewrite
- Next owner: Developer
- Developer entry: **Open — `CR_M4B_II`**
- Tester entry: **Closed — pending Developer candidate**

## Current disposition

- M4A remains Accepted and read-only unless a regression task explicitly names it.
- USER directed a clean rewrite of M4B design, production implementation and tests. The prior
  M4B-MVA-001/002 design and its action-envelope, fresh-Conversation, fake-prewarm and fixed 8/48/768
  recycle behavior are not current authority or compatibility targets.
- Designer-owned legacy M4B authority remains outside active design. The stable design path now contains the
  clean replacement cognition/product authority; it does not restore legacy compatibility.
- POC EFFICIENCY-003 and PROMPT-V2D2-004 remain valid redesign inputs. They are not themselves the
  product contract.
- Generic EventBus, State Manager, Resource Manager, offline/privacy, process isolation and Level
  1/2/3 convergence remain accepted foundations; the rewrite does not reopen M4A or unrelated
  milestones.

## Gate status

`M4B-DESIGN-GATE-REASONER-BEHAVIOR` closed by USER and Designer on 2026-09-10. The blocking
architecture gate `M4B-FOUNDATION-ARCH-REVIEW` closed on 2026-09-10 after Architect revision,
Reviewer PASS and Designer confirmation in
[`AR_impl_M4B_III`](../reviews/history/AR_impl_M4B_III.md). The confirmed authority covers sequential
Conversation replacement, post-action rest/next-turn routing, pre-perception Conversation readiness
and the R1/R2/R3/E1 boundary. Developer entry remained closed while Designer prepared the resulting
foundation design.

Designer completed [`m4b_foundation_revision`](../implement/m4b_foundation_revision.md) on
2026-09-10. Tester supplied independent coverage and Designer closed the mapping gate after Round 3
PASS in [`TR_spec_M4B_V`](../reviews/history/TR_spec_M4B_V.md). The foundation implementation package
was opened to Developer; cognition/product work remains closed.

After Developer correction, Tester independently reported PASS and Designer resolved both
Blocking findings in [`CR_M4B_I`](../reviews/history/CR_M4B_I.md) on 2026-09-11. The foundation
candidate stage is closed: focused **68**, immutable baseline **99 retained / 0 missing**, strict
baseline **99 passed / 0 skipped**, and full repository **770 passed / 2 pre-existing optional
audio skips / 29 deselected**. This verified delta is the Foundation completion Candidate; its
formal SHA is supplied in the USER handoff after commit and push.

Designer completed the clean replacement cognition/product authority on 2026-09-12 in
[`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md), with direct mappings in Ch 2b/10 and the new
`snowboard.llm/3` protocol. The design fixes the listen-only V2D2 product profile, exact admission,
Conversation reuse/replacement, full outcome matrix, memory/profile staging and Audio+LLM evidence contract.
The focused planned-recovery ownership review [`AR_impl_M4B_IV`](../reviews/history/AR_impl_M4B_IV.md) is Resolved.
Architect confirmed the existing architecture already makes SM the sole authorization owner for session-end
planned-recovery timing; Designer aligned M4B §5.3 without changing `arch.md`.

Independent Reviewer returned PASS with no Blocking findings in
[`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md). Designer adopted A1 by aligning the Ch 10 example
timeout and YAML indentation, adopted A2 by pinning two `spoken_length` examples in the coverage request, and
acknowledged A3 without a contract change. `M4B-DESIGN-REVIEW` is Closed.

Tester returned the new [`test_spec_M4B`](../test_spec/test_spec_M4B.md) and complete mapping. Designer independently
confirmed all 11/11 portable groups, 7/7 Pi/human evidence groups, 13 portable IDs, seven Pi/human IDs, exact prompt
hashes, `spoken_length` examples and the sorted/unique 99-node baseline. The resolved
[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md) closes `M4B-TEST-COVERAGE`; it contains no execution or
acceptance claim.

Developer work package [`CR_M4B_II`](../reviews/CR_M4B_II.md) is active for the replacement cognition/product
implementation and portable tests. Developer must first replace `status/development.md` with the exact inventory,
Test IDs, estimates, bounded commands and starting SHA. Pi/human execution, candidate creation, commit and push are
not authorized by this entry.

## Ordered exits

1. Developer implements `CR_M4B_II`, executes the complete portable/retained regression gates and returns the work
   package as `Revised`; no candidate or Pi acceptance is claimed.
2. Tester independently verifies the portable candidate and reports exact results.
3. Designer resolves implementation findings and performs final portable alignment.
4. After a separately authorized exact-SHA target gate, Tester executes Pi measurement/release/human evidence;
   Designer freezes reviewed thresholds and performs final product alignment.

## Role routing now

| Role | Read now | Action now |
| :--- | :--- | :--- |
| Designer | this file only | wait for `CR_M4B_II`; do not modify Developer work or claim candidate acceptance |
| Architect | this file only | no active architecture action |
| Reviewer | this file only | no active review action |
| Tester | this file only | no active verification action until Developer returns a portable candidate |
| Developer | this file, `status/development.md`, `reviews/CR_M4B_II.md` and only its linked authority | replace cognition/product implementation and portable tests; update development status before editing; do not commit/push or execute Pi/human acceptance |

Temporary legacy files are not normal background reading. Search them only when the USER or a new
review requests a specific historical statement, Test ID or SHA.

## Update rule

Designer only replaces this file when a gate, stage, entry state or next owner actually changes.
Progress details remain in the role-owned status file; no duplicate handoff or summary is created.
