---
requestor: Designer
owner: Developer
status: Open
severity: Blocking
---

# CR_M4B_II — replacement cognition/product rewrite

- Date: 2026-09-12
- Gate: `M4B-DEVELOPMENT-REWRITE`
- Activation: **Active after this work package and its linked authority are present in the Developer checkout**
- Candidate status: none; this is implementation work, not product acceptance

## Authority and entry

Developer first reads [`status/current.md`](../status/current.md), `status/development.md`, this work package,
[`ch_m4b_llm_production.md`](../implement/ch_m4b_llm_production.md), and the approved
[`test_spec_M4B.md`](../test_spec/test_spec_M4B.md). Read only the directly cited M4B sections of
[`protocol.md`](../protocol.md) §4, [`model_spec.md`](../model_spec.md) §6,
[`ch02b_workers.md`](../implement/ch02b_workers.md) §3 and [`ch10_config.md`](../implement/ch10_config.md) §6.

Resolved review provenance is [`AR_impl_M4B_IV`](history/AR_impl_M4B_IV.md),
[`IR_review_M4B_III`](history/IR_review_M4B_III.md) and
[`TR_spec_M4B_VI`](history/TR_spec_M4B_VI.md). Do not load retired M4B design, test specs or candidate behavior as
implementation authority.

Before editing code, replace `status/development.md` with the exact affected paths, symbols, mapped Test IDs,
estimates and bounded verification commands. Record the 40-character starting SHA. If the work-package authority is
not committed in that checkout, stop and report the missing handoff instead of implementing against an unstated
worktree delta.

## Required implementation

### WP-01 — Profile, prompt and config

- Implement `core-m4b-cognition-001`, exact V2D2 bytes/counts/hashes, grammar identity and field-by-field artifact
  attestation. No prompt/YAML personality override, fallback endpoint or system-site dependency.
- Implement strict listen-only composition and reject all legacy profile/recycle keys. Measurement and release
  profiles remain separate; do not invent memory thresholds.
- Cover `M4B-PROMPT-001`, `M4B-SEM-001`, relevant `M4B-NORM-001` and config rows.

### WP-02 — Child protocol and adapter

- Replace the legacy child wire with `snowboard.llm/3` READY/OPEN/MEASURE/GENERATE/SAFE_TEXT/RESULT/
  REQUEST_FAILED/CANCEL/CLOSE/SHUTDOWN semantics, exact identities and bounded framing.
- Implement non-mutating MEASURE, one-use ticket binding, GENERATE-only mutation, state/order rejection and
  terminal/join/cleanup/Engine-usable proofs. Preserve one Conversation across normal turns.
- Own the dedicated PID=PGID lifecycle, descendants, TERM/KILL/waitpid proof and fully attested new child after
  recovery. Cover `M4B-ADM-001`, `M4B-PREFILL-001`, `M4B-S2-001`, `M4B-WIRE-001` and `M4B-CONV-001`.

### WP-03 — Reasoner product policy

- Implement exact projection/normalization, input/context/memory admission, constrained semantic validation and the
  complete §6 outcome matrix. One turn performs at most one generation and publishes exactly one normal Fact.
- Preserve application/model speech ownership, final-speak-then-rest, KEEP/REPLACE/END, no replay and repeated R2
  without count escalation. Unsafe contract/protocol/backend paths remain E1.
- Cover `M4B-NORM-001`, `M4B-SEM-001`, `M4B-OUTCOME-001`, `M4B-MEM-001` and `M4B-PRIV-001`.

### WP-04 — SM-authorized planned recovery

- Adapter atomically marks `RECYCLE_PENDING`; Conversation cleanup proof alone must never schedule recovery.
- Implement a narrow private SM authorization seam, or an equivalent internal control with the same observable
  contract, inside the existing post-close convergence phase. Do not add a public SM state, Event, Fact or
  `LLMResponse` field; do not expose RM to Reasoner or infer capacity from spoken text.
- Adapter/composition invokes only the exact same-key schedule/wait seam after authorization. RM owns rebuild,
  timeout and barrier; SM retains session tracking and blocks wake/IDLE until READY. Cover every `M4B-REC-001` row.
- Supporting private changes in composition/SM/RM surfaces are allowed only when directly required by these approved
  assertions and must be inventoried before edit. Any public-contract change requires `IR_dev`, not improvisation.

### WP-05 — Observability, privacy and tooling

- Produce the separate prompt, runtime/context, memory and one-clock timing schemas without private content or
  audible-onset/latency claims. Remove workdirs/content and supervise recovery failure even without a next request.
- Replace `scripts/m4b_*` and `requirements/m4b/` surfaces needed for deterministic portable tests, artifact locks,
  measurement-only capture and later release-profile execution. Tooling must fail closed and remain offline.
- Pi measurement/human execution stays Pending until a clean exact-SHA candidate, target access and the later Tester
  execution gate. Developer may implement the specified harness/card schemas but may not claim Pi evidence.

### WP-06 — Tests, regression and cutover

- Implement every portable Test ID/case in `test_spec_M4B.md`; table-driven grouping is allowed only with preserved
  Test ID/case/assertion evidence. Use explicit barriers and bounded waits, never correctness sleeps.
- Retain all 99 immutable Foundation nodes, strict zero-skip behavior and affected M1/M2/M4A shared-path coverage.
  No delete/rename/skip/xfail/assertion weakening may create a green result.
- Replace current M4B production/test inventory in place. Do not restore legacy action-envelope, per-turn fresh
  Conversation, fake prewarm, fixed `8/48/768`, forced session-count or response-time ceiling behavior.
- Temporary legacy documentation inventory is removed only at the final verified cutover specified by product §12,
  not during an incomplete portable implementation.

## Candidate and verification boundary

Developer must run the complete portable catalog with the declared Python/platform matrix feasible in the working
environment, the immutable 99-node comparison and strict JUnit gate, affected shared-path regressions, full repository
suite, compile/static checks and privacy/diff checks. Missing native/Pi capability is reported separately and cannot
be converted to portable PASS or product acceptance.

Before returning the work package, update this review to `Revised` with:

1. changed paths and symbols mapped to WP-01–06 and every portable Test ID;
2. exact bounded commands, collected node IDs, exit status, pass/fail/error/skip/xfail/xpass counts and evidence
   locators;
3. immutable baseline count, retained count, missing count and list digests;
4. explicit inventory of Pending Pi/human rows and any missing target/profile input;
5. removal/replacement inventory for legacy production/tests, with no acceptance claim;
6. any design/API blocker as a separate `IR_dev` with the conflicting clauses and minimum required decision.

Do not commit, push, create a candidate or alter design/test authority without explicit USER authorization. After
Developer returns `Revised`, Tester independently verifies the portable candidate before Designer final alignment.
