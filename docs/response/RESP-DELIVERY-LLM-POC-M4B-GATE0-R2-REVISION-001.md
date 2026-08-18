# Response to Gate 0 R2 Revision 001

- **Response ID**: `RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001`
- **Income**: `docs/pm_handoff/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md`
- **Reviewed baseline**: `1d3444009a1edbf63e1b24a5e6977cbdb7203c80`
- **Branch**: `llm`
- **Response SHA**: supplied after commit; not self-prefilled
- **Finding**: `OUT-M4B-2026-007`
- **Status**: `TEAM REVISED — CORE EXACT-SHA RE-REVIEW PENDING`
- **Superseded by**: `RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002`
- **Execution boundary**: no Ubuntu candidate benchmark, Pi run or candidate evidence performed

The Core delivery was copied byte-for-byte into the local read-only income directory before review.
Its local and Core-source SHA-256 are both
`e7e452eb48f123fc7565fe03a7147a3759eeb5841f3b197cd1708e18ee42252f`.

## Finding Disposition

| Required correction | Implemented disposition |
| --- | --- |
| Locked schema validation | Runner validates the candidate manifest with the locked candidate schema and validates every emitted platform result with the locked result schema. Selector validates every input result and its aggregate against the locked selection schema. |
| Complete immutable identity | Lock verification now covers catalog, both schemas, validator, runner and selector. Results bind lock, manifest, run, platform, canonical command and runtime/model/config checksums. Cross-platform selection requires one unchanged manifest/pairing and stable identities. |
| Portable gate execution | Runner launches the bound argv and drives P1/P2/P3/P4/P5/P6/P8/P11 itself. It no longer accepts candidate-supplied bulk expected JSON as proof. |
| Timeout, exit and cleanup | READY/request/outer bounds are fixed. Success requires ACK, exit 0 and absent process group; all failure paths use bounded group TERM→KILL→wait and emit cleanup proof. |
| Two-platform deterministic selection | Selector requires x86_64 and aarch64 for one pairing, rejects duplicate/incomplete/drifted evidence, ranks by frozen RSS/tok/s/TTFT keys and returns at most two proposed finalists or evidence-backed no-go. |
| False-PASS regression | `CAND-NO-LLM-REPRO` invokes a program that prints validator-generated expected JSON but implements no protocol. It now returns runner `FAIL`, exit 1, P1 not-PASS and absent process group, and cannot enter `proposed_finalists`. |

## Authoritative Packet and Direct Impact Paths

- `poc_llm/tests/gate1/GATE1-PACKET-002.md`
- `poc_llm/harness/gate1-lock.json`
- `poc_llm/tools/run_gate1_prescreen.py`
- `poc_llm/tools/select_gate1_finalists.py`
- `poc_llm/fixtures/gate1/candidate.schema.json`
- `poc_llm/evidence/gate1/gate1-result.schema.json`
- `poc_llm/evidence/gate1/gate1-selection.schema.json`
- `poc_llm/tests/gate1/test_gate1_packet.py`

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/llm_poc_pycache_gate0r2 python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
python3 poc_llm/harness/gate1_validator.py --catalog poc_llm/fixtures/gate1/catalog.json --self-test
python3 poc_llm/tools/run_m4b_gate.py --gate 2A --cases P1,P2,P3,P4,P5,P6,P7,P8,P10A,P11,P12 --plan-only
python3 poc_llm/tools/run_m4b_gate.py --gate 2B --cases P1,P2,P3,P4-HOT,P5,P7,P8,P9,P10B,P11,P12 --plan-only
```

Expected and observed packet regression result: two tests `OK`; protocol test flow PASS; no-LLM
printer FAIL/nonzero and excluded from finalists; deterministic selector capped at two. Validator
self-test remains PASS. Gate 2 commands remain planning-only and must report `PLAN_VALID` with
`execution_performed=false`.

## Changed Files

- `docs/DOCUMENT_INDEX.md`
- `docs/delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md`
- `docs/milestone/README.md`
- `docs/milestone/m2_llm_candidate_evaluation.md`
- `docs/milestone/m4b_execution_plan.md`
- `docs/pm_handoff/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md`
- `docs/response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md`
- `docs/response/RESP-PM-OUT-260817-015.md`
- `poc_llm/README.md`
- `poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md`
- `poc_llm/evidence/gate1/gate1-result.schema.json`
- `poc_llm/evidence/gate1/gate1-selection.schema.json`
- `poc_llm/fixtures/gate1/candidate.schema.json`
- `poc_llm/harness/gate1-lock.json`
- `poc_llm/requirements-gate1.lock`
- `poc_llm/tests/gate1/CAND-NO-LLM-REPRO.json`
- `poc_llm/tests/gate1/CAND-PROTOCOL-SELFTEST.json`
- `poc_llm/tests/gate1/GATE1-PACKET-002.md`
- `poc_llm/tests/gate1/fake_candidate.py`
- `poc_llm/tests/gate1/fake_config.json`
- `poc_llm/tests/gate1/fake_model.artifact.txt`
- `poc_llm/tests/gate1/no_llm_printer.py`
- `poc_llm/tests/gate1/test_gate1_packet.py`
- `poc_llm/tools/run_gate1_prescreen.py`
- `poc_llm/tools/select_gate1_finalists.py`

## Core Decisions Still Required

- Complete valid P4 evidence below the starting target remains `Core threshold decision required`.
- No 4GB exception is assumed; an 8GB result cannot repair a 4GB mandatory miss.
- Accepted Audio final handoff ID/full SHA/kit remains unavailable, so Gate 2B stays `Blocked`.
- Future Gate 1 finalist, Gate 2A provisional finalist and Gate 2B final winner decisions remain
  Core-owned after their respective real evidence. None is asserted by these test-only regressions.

`0cff62f...` and `1d3444...` remain intact. This response requests re-review only of the new exact
SHA, `OUT-M4B-2026-007`, its direct impact surface and newly introduced regressions.
