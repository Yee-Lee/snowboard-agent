# Gate 1 R5 Platform-Config ACK Intake

- **Record ID**: `ACK-LLM-M2-GATE1-PLATFORM-CONFIG-R5-INTAKE-001`
- **Incoming ACK**: `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001`
- **Incoming SHA-256**: `41040791fce1c92f6eaa495dbd961378fee49bc98f8247eebee589ebd8bf6247`
- **Finding**: `M2-G1-PLATFORM-CONFIG-001`
- **Status**: `R5 EXACT SHA SUBMITTED FOR CORE REVIEW / REAL EXECUTION BLOCKED`
- **Date**: 2026-08-21

## Authority mapping

Core accepts the R4 single-config finding and authorizes one append-only `G1-X86-PI-COMPAT-005`
repository revision.  R4 remains historical; M1 protected paths remain frozen.  This intake does
not start M2 and does not authorize a real x86 run, Pi access, transfer, install, network change,
finalist decision, model baseline selection, Gate 2A or product integration.

R5 introduces an exact two-key candidate map, `configs.ubuntu-x86_64` and
`configs.pi-debian13-aarch64`.  `candidate-v5.schema.json` rejects absent, extra and legacy
singular entries.  `acquisition-v5.schema.json` adds platform-native deployed-model and
adapter/binding authentication alongside runtime, dependency and offline install identity.
`gate1_r5_projection.py` selects one platform only, hashes its strict config, validates it through
the unchanged M1 schema, and compares its path/checksum fields against the selected acquisition
entry and shared logical model.

## Verification status

The R5 synthetic suite passed 7/7: exact platform projections; missing/extra/legacy/reused config
rejection; swapped config and adapter drift rejection; strict-config runtime/model drift rejection;
actual config-file hash drift rejection; forged R4 result rejection; and Gate 1-to-Gate 2 carry-over
rejection.  R5 validator self-test passed.  The M1 protected-path diff is empty and the M1 contract
suite passed 20/20.

The R4 retained suite has passed 9/9.  Its combined invocation exceeds this environment's
single-command return limit during later Pi-cleanup work, so each deterministic case was also run
individually: x86 cap; Pi PASS filtering; Pi FAIL/INCONCLUSIVE; third-candidate backfill; forged
identity; unapproved platform/incomplete P4; Pi cleanup/orphan; dirty/reused raw directory; and
Gate 1-to-Gate 2 carry-over.  All returned exit code 0.

## Remaining blockers

1. Core must accept exact R5 SHA `190a827b4c82279e4300af6075e2eeb52b91cd54`.
2. Real Gate 1 still additionally needs capacity, controlled
   paths, operator/runner authorization, Pi access and execution authorization.

## Committed review target

- Branch: `llm`
- Exact commit: `190a827b4c82279e4300af6075e2eeb52b91cd54`
- Remote state at submission: `origin/llm` resolves to the same exact commit.
- No real x86/Pi execution or Gate 2 evidence occurred.
