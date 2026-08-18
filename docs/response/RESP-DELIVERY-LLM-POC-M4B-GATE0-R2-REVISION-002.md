# Response to Gate 0 R2 Revision 002

- **Response ID**: `RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002`
- **Income**: `docs/pm_handoff/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md`
- **Reviewed baseline**: `096cd728a277db584b23a5b0c91e3e7692b672fb`
- **Branch**: `llm`
- **Response SHA**: supplied after commit; not self-prefilled
- **Findings**: `OUT-M4B-2026-007-A` through `OUT-M4B-2026-007-D`
- **Status**: `TEAM REVISED — CORE EXACT-SHA RE-REVIEW PENDING`
- **Execution boundary**: no Ubuntu candidate benchmark, Pi run or candidate evidence performed

The Core delivery was copied byte-for-byte into the local read-only income directory before review.
Its local and Core-source SHA-256 are both
`5de819d4ea2f9e07179820b1f0272167f54300843165ef249245faf059a98d8a`.

## Finding Mapping

| Finding | Implemented disposition | Regression result |
| --- | --- | --- |
| 007-A log hygiene | Catalog freezes runner-owned forbidden patterns. Runner ignores candidate claims, scans captured stderr and protocol frames, and emits only checksum/count/sentinel IDs. Any hit forces P3/overall `FAIL`. | Candidate writes `raw model output: SECRET_PAYLOAD` while claiming no hits: exit 1, P3/overall `FAIL`, both sentinel IDs recorded. |
| 007-B cold P4 | Result schema and runner now require cold and hot total latency, TTFT, output-token and derived tok/s raw arrays plus P50/P95. Selector recomputes sample and aggregate consistency. | Missing cold TTFT: exit 1, P4/overall `FAIL`; never PASS or threshold disposition. |
| 007-C orphan cleanup | Cleanup checks the process group independently of leader state, performs bounded TERM→check→KILL→check, reaps the leader and records escalation. Escalation after normal shutdown is P1/overall `FAIL`. | Leader exits after spawning a same-group child: runner sends TERM, reports group absent, returns FAIL, and PID is absent before return. |
| 007-D selector authentication | PASS/threshold schema forbids unavailable identities. Selector requires supplied manifests, matches fixed identities to the loaded lock, verifies candidate/platform commands, exact catalog pairs, locked validator results, P4 aggregates and clean exit. | Two all-`UNAVAILABLE` handcrafted PASS files: nonzero selector result and no proposed finalist. |

## Authoritative Packet and Direct Impact Paths

- `poc_llm/tests/gate1/GATE1-PACKET-003.md`
- `poc_llm/harness/gate1-lock.json`
- `poc_llm/tools/run_gate1_prescreen.py`
- `poc_llm/tools/select_gate1_finalists.py`
- `poc_llm/fixtures/gate1/catalog.json`
- `poc_llm/evidence/gate1/gate1-result.schema.json`
- `poc_llm/evidence/gate1/gate1-selection.schema.json`
- `poc_llm/tests/gate1/test_gate1_packet.py`

## Verification Commands and Results

Official suite:

```sh
PYTHONPYCACHEPREFIX=/tmp/llm_poc_r2rev2_unittest python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
```

Observed: six tests ran in 60.600 seconds; `OK`. The protocol flow PASS is test-only. The earlier
expected-JSON printer and all four Revision 002 reproductions are non-PASS/selector-ineligible.

Four focused negative commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_a_runner_owns_log_hygiene
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_b_missing_cold_metrics_is_non_pass
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_c_cleanup_reconciles_child_after_leader_exit
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_d_selector_rejects_unavailable_handcrafted_pass
```

Observed in the official suite: all four `ok`. The validator and Gate 2 planning checks remain:

```sh
python3 poc_llm/harness/gate1_validator.py --catalog poc_llm/fixtures/gate1/catalog.json --self-test
python3 poc_llm/tools/run_m4b_gate.py --gate 2A --cases P1,P2,P3,P4,P5,P6,P7,P8,P10A,P11,P12 --plan-only
python3 poc_llm/tools/run_m4b_gate.py --gate 2B --cases P1,P2,P3,P4-HOT,P5,P7,P8,P9,P10B,P11,P12 --plan-only
```

Expected: validator `PASS`; both Gate 2 commands `PLAN_VALID` and
`execution_performed=false`.

## Changed Files

- `docs/DOCUMENT_INDEX.md`
- `docs/delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md`
- `docs/milestone/README.md`
- `docs/milestone/m2_llm_candidate_evaluation.md`
- `docs/milestone/m4b_execution_plan.md`
- `docs/pm_handoff/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md`
- `docs/response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md`
- `docs/response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md`
- `docs/response/RESP-PM-OUT-260817-015.md`
- `poc_llm/README.md`
- `poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md`
- `poc_llm/evidence/gate1/gate1-result.schema.json`
- `poc_llm/evidence/gate1/gate1-selection.schema.json`
- `poc_llm/fixtures/gate1/catalog.json`
- `poc_llm/harness/gate1-lock.json`
- `poc_llm/tests/gate1/CAND-LOG-LEAK-REPRO.json`
- `poc_llm/tests/gate1/CAND-ORPHAN-REPRO.json`
- `poc_llm/tests/gate1/CAND-P4-COLD-REPRO.json`
- `poc_llm/tests/gate1/CAND-PROTOCOL-SELFTEST.json`
- `poc_llm/tests/gate1/GATE1-PACKET-003.md`
- `poc_llm/tests/gate1/fake_candidate.py`
- `poc_llm/tests/gate1/test_gate1_packet.py`
- `poc_llm/tools/run_gate1_prescreen.py`
- `poc_llm/tools/select_gate1_finalists.py`

## Core Decisions Still Required

- A complete valid P4 measurement below the starting target remains
  `Core threshold decision required`; incomplete evidence cannot use this result.
- No 4GB exception is assumed; an 8GB result cannot repair a 4GB mandatory miss.
- Accepted Audio final handoff ID/full SHA/kit remains unavailable, so Gate 2B stays `Blocked`.
- Future Gate 1 finalist, Gate 2A provisional finalist and Gate 2B final winner decisions remain
  Core-owned after their respective real evidence.

Commits `0cff62f...`, `1d3444...` and `096cd7...` remain intact. This response requests re-review
only of the new exact SHA, findings 007-A～D, their direct impact surface and introduced regressions.
