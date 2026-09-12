# Current handoff

- Updated: 2026-09-12
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B cognition/product test-spec authoring
- Next owner: Tester
- Developer entry: **Closed**
- Tester entry: **Open — specification only**

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

Replacement coverage request [`TR_spec_M4B_VI`](../reviews/TR_spec_M4B_VI.md) is now active. Tester may create only
the new `docs/test_spec/test_spec_M4B.md` and update that review; production code, executable tests, Pi/candidate
execution and acceptance claims remain closed. Cognition/product Developer entry remains closed until Tester returns
the spec/mapping and Designer resolves the coverage gate.

## Ordered exits

1. Tester creates the replacement M4B test specification and returns `TR_spec_M4B_VI` as `Revised` with complete
   portable and Pi/human evidence mapping.
2. Designer confirms the replacement coverage mapping, resolves the review and closes the coverage gate.
3. Designer opens the cognition/product rewrite package. Developer replaces M4B production/tests
   and removes the temporary legacy inventory at cutover.
4. Tester verifies the replacement portable and Pi candidate; Designer performs final alignment.

## Role routing now

| Role | Read now | Action now |
| :--- | :--- | :--- |
| Designer | this file only | wait for `TR_spec_M4B_VI`; do not open Developer entry |
| Architect | this file only | no active architecture action |
| Reviewer | this file only | no active review action |
| Tester | this file, `reviews/TR_spec_M4B_VI.md` and only its linked authority sections | create `test_spec/test_spec_M4B.md`, update the review to `Revised`; do not implement tests or execute a candidate |
| Developer | this file only | no active implementation action |

Temporary legacy files are not normal background reading. Search them only when the USER or a new
review requests a specific historical statement, Test ID or SHA.

## Update rule

Designer only replaces this file when a gate, stage, entry state or next owner actually changes.
Progress details remain in the role-owned status file; no duplicate handoff or summary is created.
