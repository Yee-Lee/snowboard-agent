# LLM POC Gate 0 Initial Manifest R2

- **Delivery ID**: `POC-llm-DEL-2026-001-R2`
- **Core revision**: `2026-08-17 / PM-OUT-260817-015`
- **Repository / branch**: `poc_llm/snowboard-agent` / `llm`
- **Delivery HEAD**: supplied in the post-commit response; not self-prefilled
- **Status**: `SUBMITTED R2 — PENDING CORE DESIGNER EXACT-SHA INTAKE`
- **Owner**: LLM POC Technical Lead

## Authoritative Artifacts

| Item | Path | State |
| --- | --- | --- |
| Revised Core contract | `docs/pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md` | `Received; 2026-08-17 revision` |
| 015 handoff | `docs/pm_handoff/PM-OUT-260817-015-llm-poc-contract-plan-review.md` | `Received` |
| Receipt R2 | `docs/delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md` | `Submitted R2` |
| 015 response | `docs/response/RESP-PM-OUT-260817-015.md` | `Team revised; Core closure pending` |
| Unique crosswalk | `docs/milestone/m4b_traceability_crosswalk.md` | `Controlled` |
| Execution plan | `docs/milestone/m4b_execution_plan.md` | `Authoritative planning packet` |
| Gate 1 packet | `poc_llm/tests/gate1/GATE1-PACKET-001.md` | `Frozen scaffold; execution not authorized` |
| Fixture catalog | `poc_llm/fixtures/gate1/catalog.json` | `20 cases × 3 repetitions; self-test PASS` |
| Validator / lock | `poc_llm/harness/gate1_validator.py` / `poc_llm/harness/gate1-lock.json` | `v1.0.0; checksums frozen` |
| Ubuntu runner | `poc_llm/tools/run_gate1_prescreen.py` | `Prepared; no candidate run` |
| Gate 2 plan validator | `poc_llm/tools/run_m4b_gate.py` | `2A/2B PLAN_VALID; hardware execution blocked` |
| Candidate/result schemas | `poc_llm/fixtures/gate1/candidate.schema.json` / `poc_llm/evidence/gate1/gate1-result.schema.json` | `Prepared` |

## Gate and Evidence State

- Gate 0 R2: `Submitted; Core exact-SHA intake pending`.
- Internal M0: `NOT_STARTED`; prior local dummy self-test is not hardware evidence.
- Gate 1: `Blocked pending Gate 0 completion, candidates, runners and approvals`.
- Gate 2A P1–P8/P10A/P11/P12: `Blocked pending Gate 1 ACK`.
- Gate 2B P9/P10B/regression: `Blocked pending 2A provisional ACK and Accepted Audio package`.
- No model/runtime artifact was downloaded or committed. No Ubuntu/Pi candidate evidence exists.
- Raw evidence: not created; future raw data stays outside Git with reviewed checksums only.

## Platform and Dependency State

| Dependency | State |
| --- | --- |
| Ubuntu x86_64 runner/owner | `Pending` |
| Native Ubuntu aarch64 runner/owner | `Blocked` |
| Pi 5 4GB mandatory, swap=0 | `Blocked pending operator authorization` |
| Pi 5 8GB informational | `Blocked pending operator authorization` |
| Accepted Audio final handoff ID/full SHA/kit | `Blocked; Core intake pending` |
| Candidate runtime/model/quantization manifests | `Pending Gate 1` |
| Internal Tester | `Pending assignment` |

## Next Authorized Work

1. Submit this R2 packet in one new commit after `0cff62f...`; do not amend prior history.
2. Await Core exact-SHA Gate 0 intake.
3. Prepare candidate manifests and runner/resource approvals without downloading or benchmarking.
4. Do not run Ubuntu Gate 1, Pi Gate 2A or combined Gate 2B until each entry authorization exists.

## Core Decisions Still Needed

- P4 disposition when valid Pi measurements miss the negotiable target.
- Any explicit exception for a 4GB mandatory miss; 8GB data alone cannot decide acceptance.
- Accepted Audio final handoff ID/full SHA/kit that unlocks Gate 2B.
- Gate 1 finalist approval and Gate 2A/2B ACK decisions after future evidence.
