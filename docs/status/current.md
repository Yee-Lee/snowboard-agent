# Current handoff

- Updated: 2026-09-10
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B foundation implementation design
- Next owner: Designer
- Developer entry: **Closed**
- Tester entry: **Closed**

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

`M4B-DESIGN-GATE-REASONER-BEHAVIOR` closed by USER and Designer on 2026-09-10. The active blocking
architecture gate `M4B-FOUNDATION-ARCH-REVIEW` closed on 2026-09-10 after Architect revision,
Reviewer PASS and Designer confirmation in
[`AR_impl_M4B_III`](../reviews/history/AR_impl_M4B_III.md). The confirmed authority covers sequential
Conversation replacement, post-action rest/next-turn routing, pre-perception Conversation readiness
and the R1/R2/R3/E1 boundary. Developer and Tester entry remain closed until the resulting foundation
design is ready for coverage handoff.

## Ordered exits

1. Designer prepares the foundation-contract implementation design; Tester supplies its coverage.
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
| Designer | this file, `status/design.md` and the confirmed `arch.md` sections cited by `AR_impl_M4B_III` | prepare only the foundation-contract implementation design; do not open Developer entry |
| Architect | this file only | no active architecture action |
| Reviewer | this file only | deferred until a later focused review is explicitly routed |
| Tester | this file only | deferred until Designer routes the new foundation design for coverage; do not reuse the legacy M4B test contract |
| Developer | this file and `status/development.md` | stop; no active work package and no source/test edits |

Temporary legacy files are not normal background reading. Search them only when the USER or a new
review requests a specific historical statement, Test ID or SHA.

## Update rule

Designer only replaces this file when a gate, stage, entry state or next owner actually changes.
Progress details remain in the role-owned status file; no duplicate handoff or summary is created.
