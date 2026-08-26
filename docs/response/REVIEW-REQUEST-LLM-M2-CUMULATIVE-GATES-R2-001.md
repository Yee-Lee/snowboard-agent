# REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-R2-001

- **Date**: 2026-08-26
- **From**: LLM POC Technical Lead
- **To**: Independent Reviewer
- **Status**: `APPROVED BY ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE`
- **Responds to**: `docs/reviews/REVIEW-LLM-M2-CUMULATIVE-REDESIGN-001.md`
- **Requested disposition**: `APPROVE` or itemized `REVISE`

## Scope

This R2 request addresses only the two blocking findings retained by the latest review. All execution
remains stopped. No model, P5 or Pi run was performed, and no commit, push or Core delivery is
authorized by this response.

## Finding 1 — recursive Git invalidation

### Revision

- Gate 1 still records its clean exact Git `execution_sha`, but only for chronological provenance.
- Gate 1 now records `execution_surface_sha256`, the SHA-256 of
  `poc_llm/harness/gate1-pi-compat-lock-v7.json`.
- Gate 2A requires the Gate 1 execution commit to be an ancestor of the current clean checkout. It
  must not require direct SHA equality.
- Carry-forward is decided by the execution-surface lock digest plus affected runtime/model/config/
  protocol/fixture/Pi/environment/manifest identities.
- Later evidence, ACK, delivery or milestone-documentation commits therefore do not invalidate Gate
  1. A changed locked execution artifact still invalidates its affected P items.

Current uncommitted Gate 1 lock digest for review:
`480adb939a6bfc359dfc2a10c9d478cece94df8fd24f8c48bb810d902e06d8d2`.
The runtime recomputes this value and records it in artifact receipts, the sanitized aggregate and
the cumulative receipt; no digest is embedded in the lock itself, so there is no hash recursion.

Review:

- `poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md` revision r3
- `poc_llm/tools/run_gate1_pi_compat_v7.py`
- `poc_llm/evidence/gate1/gate1-pi-compat-v7-result.schema.json`
- `poc_llm/evidence/m4b/pi-artifact-auth-receipt-v2.schema.json`
- `poc_llm/evidence/m4b/gate1-cumulative-receipt-v7.schema.json`
- `poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md` revision r2

### Required judgment

Confirm that an ancestor check plus exact execution-surface/component identities permits normal
evidence/documentation commits without allowing an execution-affecting source change to pass
silently.

## Finding 2 — P5 fast-model trap

### Revision

The old one-shot 512-token fixture is not reused by packet `002`. The replacement is
`poc_llm/fixtures/gate2/p5-continuous-timeout-002.json`, SHA-256
`3747158b1f7400e683ced92061901787dd5634a55e50f3ed381eda11c53a94d8`.

It defines one outer operation and one immutable 15-second timer. The adapter repeatedly invokes the
real model with the same public extreme input and a maximum of 512 output tokens per chunk. EOS or
valid completion of a chunk has the predeclared disposition `CONTINUE`; it immediately begins the
same next chunk and cannot emit `RESULT`. At the outer deadline, the adapter cancels the currently
owned operation and must emit correlated `TIMEOUT` during 15–17 seconds, recover READY, pass a
standard-config rebuild probe and prove zero residue.

This rule is fixed before either candidate runs. It does not inspect speed to choose another fixture,
does not call a fast completion PASS and does not create a Core replacement-disposition round. An
early `RESULT` is a packet defect (`INCONCLUSIVE`); actual candidate timeout/cancel/recovery failure is
`FAIL`.

Review:

- `poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md` section G2A-WP03
- `poc_llm/fixtures/gate2/p5-continuous-timeout-002.json`
- `docs/response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001.md`
- `docs/milestone/m4b_execution_plan.md`

### Required judgment

Confirm that the predeclared continuous-chunk operation necessarily reaches the real timeout path for
both fast and slow models while preserving the contract requirement to test interruption, child
health and recovery.

## Pure validation

```text
python3 -m unittest \
  poc_llm.tests.gate1.test_gate1_pi_packet_v7 \
  poc_llm.tests.gate1.test_install_gate1_arm64_wheel \
  poc_llm.tests.gate2.test_pi_packet_definitions

Ran 25 tests in 3.936s
OK
```

New negative checks reject a missing execution-surface field and verify that packet `002` binds Git
ancestor semantics plus the continuous P5 fixture. Existing lock, one-pass hash, schema, lifecycle,
P10A and fatal-exit checks remain green.

## Response rule

Return `APPROVE` only if both blocking findings are closed. Otherwise return `REVISE` with exact file
and required correction. Even `APPROVE` does not begin execution until the User accepts it.
