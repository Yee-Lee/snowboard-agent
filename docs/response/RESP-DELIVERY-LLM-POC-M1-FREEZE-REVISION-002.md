# M1 Freeze Candidate Revision 002 — Technical Response

- **Response ID**: `RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-002`
- **In response to**: `DELIVERY-LLM-POC-M1-FREEZE-REVISION-002`
- **Reviewed predecessor**: `llm` / `93b34c14d5ee0f767ee16dd0fbbbb72e18775760`
- **Replacement candidate**: `llm` / `830d0b4ed2d41406c789bb110ed84b7553f330a4`
- **Date**: 2026-08-20
- **Status**: `TEAM REVISED / CORE DESIGNER AND INTERNAL TESTER REVIEW REQUIRED`

## Disposition

The replacement is limited to the locked `M1-FREEZE-003-R2` scope. Findings
`M1-FREEZE-001`, `M1-FREEZE-002`, and `M1-FREEZE-004` remain closed and their artifacts are
unchanged. The reviewed predecessor remains immutable.

## Direct correction and proof

- `validate_sequence()` now rejects every schema-valid frame encountered after a FATAL terminal
  outcome with `frame after FATAL`, before frame dispatch can mutate lifecycle state.
- A table-driven regression appends READY, ERROR, RESULT, CANCEL, SHUTDOWN, and SHUTDOWN_ACK to a
  valid `READY → GENERATE → PROTOCOL_ERROR/FATAL` prefix. All six must contain the terminal guard
  error.
- Only `m1_contract_validator.py`, `test_m1_contract.py`, and their two entries in
  `m1-contract-lock.json` changed in the exact candidate commit.
- FATAL closes only the child wire stream. It does not claim parent force-abort, terminate/kill,
  waitpid, outer completion, Resource Manager rebuild, or Gate 2 evidence.

## Deterministic verification

```text
python3 poc_llm/harness/m1_contract_validator.py --self-test
result=PASS; violations=[]

python3 -m unittest -q poc_llm.tests.gate1.test_m1_contract
Ran 20 tests — OK

python3 -m unittest -q \
  poc_llm.tests.gate1.test_m1_contract \
  poc_llm.tests.gate1.test_gate1_packet_v4 \
  poc_llm.tests.gate1.test_gate1_packet
Ran 35 tests — OK
```

Lock SHA-256 after the two authenticated entry updates:
`f37c19891c8353db9ac398dc3fccfbb0b834ccc971ed1137834a7cf7741b20d1`.

## Requested next decision

Core Designer should re-review only the FATAL guard and direct regression. If approved, Internal
Tester should independently review the exact candidate lock and deterministic evidence. Until both
approvals are recorded, M1 remains `IN_PROGRESS`; no M1 tag or real execution is authorized.
