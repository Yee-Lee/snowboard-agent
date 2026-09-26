# Current handoff

- Updated: 2026-09-26
- Writer: Designer only
- Current milestone: ALPHA Voice-only product convergence
- Current stage: **ALPHA Design complete；Test Spec entry open**
- Next owner: Tester
- Developer entry: **Closed pending `test_spec_ALPHA.md`**

## Gate transition facts

- M4 and M4C are Accepted; candidate `0b2160e5d48dcc959b08f4a23ede91a9e0d5640d` completed formal Pi run
  `M4C-FORMAL-PV-20260926-01` with all seven catalog entries Pass. Accepted M4 evidence remains immutable.
- USER approved the ALPHA product scope on 2026-09-26. [`ALPHA.md`](../milestones/ALPHA.md) now fixes
  `ALPHA-L01-LIFECYCLE`, `ALPHA-P01-PERFORMANCE`, `ALPHA-R01-LLM-RECOVERY` and
  `ALPHA-Q-RUN-01-QUALITY` as four independent runs.
- Lifecycle is one startup → three Sessions × two Turns → per-Session cleanup → shutdown → owner absence →
  restart run. Offline and one aggregate privacy scan are embedded; they are not separate Test IDs.
- Performance is a separate controlled run with five case-specific timing views and no numeric acceptance gate.
  Baseline is required; code optimization occurs only for a clear product bottleneck and is bounded to one selected
  improvement work item.
- Recovery is one real LLM-child failure after a safe streaming fragment, followed by full convergence, one
  replacement, a new normal Session and final owner absence. It does not reopen the accepted fault matrix.
- Quality contains six fixed cases, each executed once. The runner owns objective path results; Codex owns semantic
  judgment, and only an unresolved `NEEDS_USER_DECISION` is routed to USER.
- Resource／thermal research, soak, latency ceilings, manifest／checksum revalidation, repeated fault matrices and
  extra review／sign-off gates are outside ALPHA.

## Role routing now

| Role | Action now |
| :--- | :--- |
| Tester | Create `docs/test_spec/test_spec_ALPHA.md`; map the four authorities without adding excluded scope |
| Designer | Design authority complete；respond only to a concrete Test Spec conflict or USER scope change |
| Developer | Entry closed until Test Spec coverage is complete and routed |
| Architect / Reviewer | No active request；enter only for a focused contract conflict that accepted architecture cannot support |

Designer replaces this file only when Test Spec coverage, Developer entry, stage, gate or next owner changes.
