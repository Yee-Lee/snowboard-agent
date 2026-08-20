# LLM POC M1 Freeze Replacement Candidate R3

- **Delivery ID**: `DELIVERY-006-PM-LLM-POC-M1-FREEZE-CANDIDATE-R3`
- **In response to**: `DELIVERY-LLM-POC-M1-FREEZE-REVISION-002`
- **From / via**: LLM POC Team / User-authorized Agent courier
- **To**: Core Designer and Internal Tester
- **Branch**: `llm`
- **Exact replacement candidate SHA**: `830d0b4ed2d41406c789bb110ed84b7553f330a4`
- **Reviewed predecessor SHA**: `93b34c14d5ee0f767ee16dd0fbbbb72e18775760`
- **Date**: 2026-08-20
- **Status**: `READY FOR LOCKED-SCOPE RE-REVIEW / REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `No`

## Exact review scope

This append-only candidate closes only `M1-FREEZE-003-R2`. Its commit changes exactly:

- `poc_llm/harness/m1_contract_validator.py`
- `poc_llm/tests/gate1/test_m1_contract.py`
- the validator/tests hashes in `poc_llm/contracts/m1/m1-contract-lock.json`

The validator now treats FATAL as the end of the child wire stream. The direct table regression
proves that READY, ERROR, RESULT, CANCEL, SHUTDOWN, and SHUTDOWN_ACK are all rejected after FATAL
with `frame after FATAL`. Findings 001, 002, and 004 remain closed and unchanged.

FATAL does not prove parent cleanup, waitpid, rebuild, or outer completion and creates no Gate 2
evidence credit.

## Verification

- Contract self-test: `PASS`, zero violations
- Replacement suite: 20/20 `OK`
- Combined replacement + retained Gate 1 R4/R3 suites: 35/35 `OK`
- Updated lock SHA-256: `f37c19891c8353db9ac398dc3fccfbb0b834ccc971ed1137834a7cf7741b20d1`

Detailed response:
`docs/response/RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-002.md`.

## Requested disposition

Core Designer should approve or reject the locked FATAL guard scope. Upon Designer approval,
Internal Tester should independently verify the exact SHA, lock and deterministic evidence. Both
approvals are required before the POC Team may mark M1 complete or create the `m1` tag.

Artifact acquisition/download/install, real Ubuntu execution, Pi access/transfer/network switching
or execution, candidate selection, Gate 2A and Gate 2B remain unauthorized.
