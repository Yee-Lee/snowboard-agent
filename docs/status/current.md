# Current handoff

- Updated: 2026-09-10
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B foundation implementation
- Next owner: Developer
- Developer entry: **Open for M4B-FOUNDATION-REVISION only**
- Tester entry: **Closed until foundation candidate**

## Current disposition

- M4A remains Accepted and read-only unless a regression task explicitly names it.
- USER directed a clean rewrite of M4B design, production implementation and tests. The prior
  M4B-MVA-001/002 design and its action-envelope, fresh-Conversation, fake-prewarm and fixed 8/48/768
  recycle behavior are not current authority or compatibility targets.
- Designer-owned legacy M4B authority has been moved out of active design. The stable design path is
  a tombstone and intentionally contains no replacement product design yet.
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
is now open to Developer; cognition/product work remains closed.

## Ordered exits

1. Tester supplies foundation coverage; Designer confirms it against the approved design.
2. Designer opens only the foundation revision package. Developer migrates the affected event,
   State Manager, rest and Conversation lifecycle contracts; Tester verifies affected M1/M2
   regression without reopening their historical acceptance.
3. Designer prepares the remaining replacement M4B design from the confirmed inputs in
   `docs/status/design.md`; no legacy section is copied as a starting point.
4. Required focused review and new M4B test specification close.
5. Designer opens the cognition/product rewrite package. Developer replaces M4B production/tests
   and removes the temporary legacy inventory at cutover.
6. Tester verifies the replacement portable and Pi candidate; Designer performs final alignment.

## Role routing now

| Role | Read now | Action now |
| :--- | :--- | :--- |
| Designer | this file and `status/design.md` | await the foundation candidate; do not start the cognition/product rewrite |
| Architect | this file only | no active architecture action |
| Reviewer | this file only | deferred until a later focused review is explicitly routed |
| Tester | this file only | wait for the foundation candidate; no verification run is open yet |
| Developer | this file, `status/development.md`, [`m4b_foundation_revision`](../implement/m4b_foundation_revision.md), [`test_spec_M4B_foundation`](../test_spec/test_spec_M4B_foundation.md) and its node-ID baseline | implement only the foundation inventory and acceptance; do not modify excluded cognition/product scope |

Temporary legacy files are not normal background reading. Search them only when the USER or a new
review requests a specific historical statement, Test ID or SHA.

## Update rule

Designer only replaces this file when a gate, stage, entry state or next owner actually changes.
Progress details remain in the role-owned status file; no duplicate handoff or summary is created.
