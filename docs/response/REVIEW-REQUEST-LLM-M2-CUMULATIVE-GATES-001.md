# REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-001

- **Date**: 2026-08-26
- **From**: LLM POC Technical Lead
- **To**: Independent Reviewer
- **Status**: `SUPERSEDED BY R2 REVIEW REQUEST / EXECUTION HOLD`
- **Review target**: uncommitted cumulative Gate redesign and `G1-PI-COMPAT-007`
- **Requested disposition**: `APPROVE` or itemized `REVISE`

## Review question

Does this design produce reproducible, non-duplicative and fail-closed evidence for all P1–P12
across Gate 1, Gate 2A and Gate 2B, while correcting the v6 READY-timing defect without weakening
the formal 10-second P1 startup rule?

No Pi execution, model execution, P5 execution, commit, push or Core delivery is part of this review.
The POC must remain stopped until the Reviewer returns `APPROVE` and the User accepts that finding.

## User-directed boundary

| Stage | First formal execution | Carry-forward |
| --- | --- | --- |
| Gate 1 | P1, P6, P7, P10A, P11, P12 | accepted unchanged evidence enters final chain |
| Gate 2A | P2, P3, P4, P5, P8 | does not rerun unchanged Gate 1 items |
| Gate 2B | P9, P10B | does not rerun unchanged Gate 1/2A items |

The full P1–P12 set must be complete before final delivery. A gate transition alone never requires a
rerun. Source, runtime, model, config, protocol, fixture, Pi/environment or manifest drift invalidates
only affected evidence. P5 remains Pi-only. Core ACK may arrive after reviewer-approved execution
starts, but must arrive before P credit, finalist status or Gate 1 closure becomes final.

## Primary review set

### Boundary and status

- `docs/milestone/README.md`
- `docs/milestone/m4b_execution_plan.md`
- `docs/milestone/m4b_traceability_crosswalk.md`
- `docs/milestone/m2_llm_candidate_evaluation.md`
- `docs/milestone/m3_llm_child_pi_integration.md`
- `docs/milestone/m4_llm_combined_validation_and_delivery.md`
- `docs/response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001.md`
- `docs/response/ACK-LLM-M2-GATE1-PI-COMPAT-006-REVIEW-001.md`

### Executable packets

- `poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md`
- `poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md`
- `poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md`
- `poc_llm/harness/gate1-pi-compat-lock-v7.json`
- `poc_llm/tools/run_gate1_pi_compat_v7.py`
- `poc_llm/tools/install_gate1_arm64_wheel_v2.py`
- `poc_llm/harness/pi_artifact_auth.py`
- `poc_llm/harness/pi_runtime_v2.py`
- `poc_llm/harness/litert_lm_pi_child_adapter_v2.py`

### Schemas and fixtures

- `poc_llm/contracts/m1/strict-config-pi-v2.schema.json`
- `poc_llm/evidence/m4b/pi-artifact-auth-receipt-v2.schema.json`
- `poc_llm/evidence/gate1/gate1-pi-compat-v7-result.schema.json`
- `poc_llm/evidence/m4b/gate1-cumulative-receipt-v7.schema.json`
- `poc_llm/fixtures/gate1/pi-compat-candidates-v7.json`
- `poc_llm/fixtures/gate1/pi-configs-v7/`
- `poc_llm/fixtures/gate1/gate1-core-abort-001.json`

## Required reviewer checks

1. **Cumulative completeness** — the three packets assign every P1–P12 item exactly once and define
   a sufficiently strict affected-evidence invalidation rule.
2. **v6 correction** — `006` is retained as packet-defect evidence only; no candidate failure,
   zero-finalist finding or P credit is inferred.
3. **READY timing** — model SHA-256 completes before measured child launch. The 10-second clock still
   includes Popen, small identity checks, Engine construction and exact READY emission.
4. **Artifact identity** — each model is an absolute read-only regular file, streamed once, and
   bound to device/inode/mode/size/mtime/ctime. Child and rebuild paths do not reread model contents.
5. **Schema identity** — config, protocol, prompt, response and receipt schemas are hash-bound in
   every child launch; candidate/config/runtime/model pairings are immutable.
6. **P1/P10A** — one persistent Engine supplies the normal lifecycle and exactly twenty stability
   sessions; all samples enter the frozen slope/median/thermal decision with no dropped sample.
7. **P6/P7** — native cancel, completed-before-cancel, no-terminal and force-abort branches cannot
   claim P7 without an observed active generation, bounded process-group cleanup, rebuild, recovery
   generation, clean shutdown and fatal-controller exit `4`.
8. **P11/P12** — provenance/license, clean offline install, native ELF/linkage, pre/post target,
   offline, swap, throttling, metadata and log-hygiene checks support their claimed scope.
9. **Result semantics** — authenticated acceptance-rule violations are `FAIL`; missing packet,
   environment or measurement evidence is `INCONCLUSIVE`; P6 conditional is valid only with P7 PASS.
10. **Schema consistency** — candidate order, PASS P states, finalist cardinality and explained
    INCONCLUSIVE outcomes are machine-rejected when inconsistent.
11. **Evidence safety** — Git/sanitized output cannot contain model output, prompt/payload text,
    weights, runtime binaries, credentials or endpoints.
12. **Approval order** — review does not authorize execution; User acceptance is required before
    commit/push/Core delivery/Pi work, and benchmark/finalist publication requires later User review.

## Pure validation evidence

Executed on the workstation without loading a model or using Pi:

```text
python3 -m unittest \
  poc_llm.tests.gate1.test_gate1_pi_packet_v7 \
  poc_llm.tests.gate1.test_install_gate1_arm64_wheel \
  poc_llm.tests.gate2.test_pi_packet_definitions

Ran 24 tests in 2.408s
OK
```

Coverage includes lock authentication, read-only one-pass model hashing, metadata-drift rejection,
child no-model-reread behavior, five schema identities, license metadata, safe one-pass wheel
installation, cumulative mapping, catalog input validation, P10A calculations, aggregate schema
positive/negative cases and fatal exit `4`.

## Explicit reviewer judgments

- Is 10 seconds after model authentication the correct formal P1 deadline, with no model hash or
  transfer time inside it?
- Is read-only mode plus full stat identity sufficient for receipt reuse within one controlled run?
- Is P6 `Conditional escalation` acceptable for completed-before-cancel only when the complete P7
  fallback path passes?
- Are P10A thresholds and twenty-session reuse strong enough to avoid a second stability run?
- Is affected-item-only invalidation sufficiently conservative for Gate 1 evidence carry-forward?

## Response format

Return `APPROVE` only if all twelve checks pass. Otherwise return `REVISE` with file, line or symbol,
severity, rationale and required correction for each finding. Reviewer approval must identify the
reviewed worktree diff or, after the later milestone commit, the exact source SHA.
