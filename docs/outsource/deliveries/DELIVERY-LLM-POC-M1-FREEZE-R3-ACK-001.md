# Core Designer → PM → LLM POC Team: M1 Freeze Candidate R3 ACK

- **Delivery ID**: `DELIVERY-LLM-POC-M1-FREEZE-R3-ACK-001`
- **In response to**: `DELIVERY-006-PM-LLM-POC-M1-FREEZE-CANDIDATE-R3`
- **Reviewed POC branch / exact candidate**: `llm` / `830d0b4ed2d41406c789bb110ed84b7553f330a4`
- **Candidate parent**: `c639c77a821c7a8d259f9623fcda4752facdeacf`
- **From**: Core Team Designer
- **To**: PM, LLM POC Team and Internal Tester
- **Date**: 2026-08-20
- **Status**: `DESIGNER ACCEPTED — CANDIDATE FROZEN / INTERNAL TESTER SIGN-OFF PENDING`
- **Real execution authorization**: `Not authorized`
- **Architecture change**: `No`

## 1. Final Designer disposition

Core Designer accepts exact candidate
`830d0b4ed2d41406c789bb110ed84b7553f330a4` and records it as the **frozen M1 candidate**.
The only open R2 finding, `M1-FREEZE-003-R2`, is closed. No new Blocking finding is introduced.

The candidate commit changes exactly the three authorized protected inputs:

- `poc_llm/harness/m1_contract_validator.py`
- `poc_llm/tests/gate1/test_m1_contract.py`
- the validator and tests hashes in `poc_llm/contracts/m1/m1-contract-lock.json`

The later documentation-only commit `a3b5b7c5e6b25d3c0957553f50d0a0683ca597f9` does not replace the
candidate identity. Internal verification and any later M1 tag must continue to identify the full candidate SHA
`830d0b4ed2d41406c789bb110ed84b7553f330a4`.

## 2. Locked-scope finding closure

| Finding | R3 disposition | Evidence |
| :--- | :--- | :--- |
| `M1-FREEZE-001` | **Closed; not reopened** | R3 does not modify response, P5, schema or log-hygiene behavior. |
| `M1-FREEZE-002` | **Closed; not reopened** | R3 does not modify Core/child input projection or request identity. |
| `M1-FREEZE-003-R2` | **Closed** | `validate_sequence` rejects every schema-valid frame after FATAL; the table regression covers READY, ERROR, RESULT, CANCEL, SHUTDOWN and SHUTDOWN_ACK. |
| `M1-FREEZE-004` | **Closed; not reopened** | R3 changes only the two expected lock entries and does not alter candidate/config identity behavior. |

FATAL remains only a child-wire terminal outcome. This ACK does not claim parent cleanup, `waitpid`, rebuild,
outer completion, Gate 2 evidence or target execution credit.

## 3. Independent Designer verification

Core exported the exact candidate SHA to an isolated temporary tree; the LLM POC repository was not modified.

```text
validator SHA-256 = 4a28f4feb5cd0b24e0eb11838f82f1586cee2b3dd5eb12f62cfed33fd69b0b39
tests SHA-256     = f7996ee728a8a8d1947acc5c70c9ec1f8e3c02f3353b7982c4b89b79fb943685
lock SHA-256      = f37c19891c8353db9ac398dc3fccfbb0b834ccc971ed1137834a7cf7741b20d1

python3 poc_llm/harness/m1_contract_validator.py --self-test
result=PASS; violations=[]

python3 -m unittest -v poc_llm.tests.gate1.test_m1_contract
Ran 20 tests in 2.820s — OK

timeout 180s python3 -m unittest -q \
  poc_llm.tests.gate1.test_m1_contract \
  poc_llm.tests.gate1.test_gate1_packet_v4 \
  poc_llm.tests.gate1.test_gate1_packet
Ran 35 tests in 93.416s — OK; exit 0
```

## 4. Exact remaining gate

Internal Tester should now independently check the same full SHA and run only the following bounded scope:

1. verify the three hashes above against `m1-contract-lock.json`;
2. run the contract self-test and require `PASS` with zero violations;
3. run the 20-test replacement suite and the retained 35-test combined suite with a timeout of at least 180 seconds;
4. confirm the candidate-affecting paths are unchanged from exact SHA `830d0b4...`.

If these checks pass, Internal Tester may issue M1 sign-off without another Designer review. A failure must name the
exact mismatched path, command, exit code and assertion. It must not reopen findings 001, 002 or 004, add preference
work, or require real Ubuntu/Pi execution for this contract-freeze decision.

## 5. Freeze and authorization boundary

- Designer freeze is effective for exact SHA `830d0b4ed2d41406c789bb110ed84b7553f330a4`.
- Any later change to contract schemas, fixtures, boundary, validator, tests or lock revokes this freeze and requires
  a new append-only candidate SHA plus the affected deterministic checks.
- M1 completion and creation of the POC `m1` tag remain pending only on Internal Tester sign-off. On PASS, the tag
  must identify the exact frozen candidate SHA, not the later documentation commit.
- Artifact acquisition/download/install, real Ubuntu execution, Pi access/transfer/network switching/execution,
  candidate selection, Gate 2A and Gate 2B remain unauthorized.

No further LLM POC code revision is requested by Designer.
