# Current handoff

- Updated: 2026-09-13
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B exact-tuple target authorization
- Next owner: Tester + Designer
- Developer entry: **Closed — replacement implementation is portable-aligned**
- Tester target entry: **Pending — independently validate and co-approve the exact measurement tuple before execution**
- Portable-frozen candidate: `9ffd6e17ad5504d53c7c18799ca4718f69988f7e`
  (`origin/core`; portable PASS, not Accepted or target-authorized)

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

Developer returned work package [`CR_M4B_II`](../reviews/history/CR_M4B_II.md) **Revised** with WP-01–06 implemented,
including the authorized exact ticket-disposal path. USER authorized commit and push; the resulting provisional
portable candidate is exact SHA `9e005e48fe1582c901fcba3eb152747c92c43890` on `origin/core`. Designer independently confirmed that the
candidate contains the declared work-package scope, the local `origin/core` tracking ref resolves to the same full
SHA, and the candidate checkout was clean before this Designer-only status update. Developer Pi/Linux runs are
diagnostics only and are not Tester evidence or acceptance.

Tester portable entry is now Open for independent verification of that exact SHA. Candidate protected inputs are
immutable for this verification round: any source, test, dependency/lock, config-contract or candidate-runner change
requires an append-only fix commit and a new candidate. Native PM, product cards and human semantic/audio rows remain
Pending; this transition neither supplies dual-role target authorization nor claims a native, human or product PASS.

Developer opened Blocking [`IR_dev_M4B_IV`](../reviews/history/IR_dev_M4B_IV.md) after proving that the original MEASURED
state had no legal token-limit R1 continuation which both kept the Conversation and invalidated its ticket.
Designer confirmed the gap, rejected delayed next-MEASURE supersession, and revised product/protocol authority to
require exact `DISCARD_TICKET` / `TICKET_DISCARDED` proof before R1. The operation preserves generation, revision,
history and KV; disposal mismatch/failure is E1. This is a private protocol/adapter correction with no public
SM/Event/Fact/response or architecture change. Focused Tester request
[`TR_spec_M4B_VII`](../reviews/history/TR_spec_M4B_VII.md) is Resolved after Designer confirmed all 9/9 requested
requirements, retained all 13 portable Test IDs and found no Blocking coverage gap. Both reviews are Resolved;
their authorization is implemented in the Revised `CR_M4B_II` candidate. No Tester, native or product PASS is
claimed by this handoff.

Tester independently verified exact candidate `9ffd6e17ad5504d53c7c18799ca4718f69988f7e` on Pi/Linux
aarch64 with CPython 3.11.16, 3.12.14 and 3.13.15: each canonical run passed **1005** with zero
Fail/Error/Skip/XFail/XPASS. Matrix SHA-256 is
`2438944bc0ad64f48ae577ca3cd7c2e9ff1c0008174ab8d398459c8293c5fbdb`; profile and catalog
digests match approved authority. Exact-SHA runner regression passed 78/78 on every minor and the
B1/B2 negative paths fail closed. Designer found no design deviation or new high-risk regression,
resolved [`CR_M4B_II`](../reviews/history/CR_M4B_II.md), and froze protected inputs at this SHA for
the next gate. PM, PR, PH, native-model, product-card and human evidence remain Pending.

## Ordered exits

1. **Complete:** Developer rewrite, append-only B1/B2 fixes, exact candidate
   `9ffd6e17ad5504d53c7c18799ca4718f69988f7e`, independent portable PASS and Designer alignment.
2. **Active:** Tester and Designer independently validate and approve the exact candidate/profile/harness/target
   measurement tuple after required target artifacts, private config and evidence roots are available.
3. **Pending:** Tester executes PM only after dual approval; Designer and Tester then derive/freeze thresholds into
   a release profile before separate PR and PH execution. No target execution is authorized by this handoff.

## Role routing now

| Role | Read now | Action now |
| :--- | :--- | :--- |
| Designer | this file and `roles/candidate-process.md` | independently validate the complete measurement tuple and co-approve only when all target inputs exist |
| Architect | this file only | no active architecture action |
| Reviewer | this file only | no active review action |
| Tester | this file, `test_spec/test_spec_M4B.md` and `roles/candidate-process.md` | independently validate/co-approve the exact measurement tuple; do not execute PM before dual approval; keep PR/PH Pending |
| Developer | this file only | no active action; protected inputs at `9ffd6e17ad5504d53c7c18799ca4718f69988f7e` are frozen and any fix is append-only |

Temporary legacy files are not normal background reading. Search them only when the USER or a new
review requests a specific historical statement, Test ID or SHA.

## Update rule

Designer only replaces this file when a gate, stage, entry state or next owner actually changes.
Progress details remain in the role-owned status file; no duplicate handoff or summary is created.
