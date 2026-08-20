# LLM POC M1 Freeze Candidate Review Delivery

- **Delivery ID**: `DELIVERY-004-PM-LLM-POC-M1-FREEZE-CANDIDATE`
- **From / via**: LLM POC Team / User-authorized Agent courier (may be relayed by PM)
- **To**: Core Designer and Internal Tester
- **Branch**: `llm`
- **Date**: 2026-08-20
- **Status**: `READY FOR COMMIT AND PM RELAY / REVIEW REQUIRED / REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `Proposed child-boundary freeze; no product composition-root change`

## Review request

Please review the exact M1 Freeze Candidate as one packet before any real candidate result is
available. The POC Team requests one consolidated response:

1. Core Designer: `APPROVED` for the exact PromptBuilder, normalized response/P5, protocol/adapter,
   and strict-config candidate; or `REVISION_REQUIRED` with every rejected clause and replacement
   decision in the same response.
2. Internal Tester: `APPROVED` for the locked schemas, fixtures, validator, negative regressions,
   and evidence-completeness rules; or `REVISION_REQUIRED` with all missing deterministic cases.
3. Confirm that the delivered M4b contract and `core_llm_m4b_tasks.md` form the governing M1
   checklist. If another formal checklist/development guide applies, return it in the same review.

Approval freezes this candidate for M2 preparation. It does not authorize runtime/model download,
artifact acquisition/install, storage allocation, real x86 execution, Pi access/transfer/network
switching/execution, candidate selection, Gate 2A, or Gate 2B.

## Authoritative packet

- Internal review and requirement mapping:
  `docs/response/ACK-M1-FROZEN-CONTRACT-001.md`
- Frozen-candidate lock:
  `poc_llm/contracts/m1/m1-contract-lock.json`
- PromptBuilder input schema:
  `poc_llm/contracts/m1/prompt-input.schema.json`
- Normalized response schema:
  `poc_llm/contracts/m1/response.schema.json`
- Child protocol frame schema:
  `poc_llm/contracts/m1/protocol-frame.schema.json`
- Strict-config schema:
  `poc_llm/contracts/m1/strict-config.schema.json`
- Deterministic fixtures:
  `poc_llm/contracts/m1/contract-fixtures.json`
- Validator and regressions:
  `poc_llm/harness/m1_contract_validator.py` and
  `poc_llm/tests/gate1/test_m1_contract.py`

The commit message/notification accompanying this delivery supplies the immutable full SHA after
commit. This document intentionally does not predict or self-reference a future commit SHA.

## Exact freeze candidate

- Protocol `snowboard.llm/1`; single-turn PromptBuilder with payload-free pending-message count and
  restricted perception/action/tool capability view.
- Exact `speak/tool/rest` response contract and P5 apology-speak/rest fallback.
- Correlated READY/GENERATE/RESULT/CANCEL/CANCELLED/ERROR/SHUTDOWN/SHUTDOWN_ACK JSON-lines frames;
  one active generation, stale/duplicate rejection, terminal outcome and rebuild barrier.
- Gate 1 `op` commands remain adapter-side packet controls. The accepted R4 packet is not rewritten
  into the final product wire protocol and cannot receive Gate 2 credit.
- Strict config: LiteRT-LM only; 128 input / 16 output tokens; temperature 0; top-p 1; 4 threads;
  READY/generate/cancel 10,000/15,000/500ms; TERM/KILL/rebuild 2,000/1,000/10,000ms; approved
  absolute paths and SHA-256 identity; no download, network fallback, or fallback model.

Gate 1's separately accepted 180-second Pi compatibility model-load bound remains specific to the
compatibility acquisition/run phase. It does not replace the Gate 2 P1 final-child READY ≤10s gate.

## POC deterministic verification

```text
python3 -m unittest -v poc_llm.tests.gate1.test_m1_contract
Ran 5 tests — OK

python3 poc_llm/harness/m1_contract_validator.py --self-test
result=PASS; violations=[]

python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet_v4
Ran 9 tests — OK

python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
Ran 6 tests — OK
```

The contract validator authenticates seven locked artifacts, validates four Draft 2020-12 schemas,
seven schema-negative cases, two valid lifecycle sequences, three invalid lifecycle sequences, and
capability-context rules. These results are Developer/POC Team observations only, not candidate
evidence, hardware evidence, or Internal Tester confirmation.

## Requested next state

- If both reviews approve the exact packet, record the approved commit SHA and approval references,
  then continue the remaining M1 manifest/adapter/acquisition-readiness work under existing bounds.
- If revision is required, preserve this Candidate SHA and return one consolidated finding list;
  the POC Team will append a new Freeze Candidate without rewriting submitted history.
- M1 remains `IN_PROGRESS` until all exit conditions close. Real Gate 1 remains
  `NOT_STARTED / BLOCKED` pending separate execution authorization.
