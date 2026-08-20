# M1 Freeze Candidate Revision 001 — Technical Response

- **Response ID**: `RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-001`
- **In response to**: `DELIVERY-LLM-POC-M1-FREEZE-REVISION-001`
- **Supersedes**: `M1-FROZEN-CONTRACT-001` candidate at `0b5a92872f8a695b145b389168111420cd2592c5`
- **Branch**: `llm`
- **Date**: 2026-08-20
- **Status**: `TEAM REVISED / REPLACEMENT REVIEW REQUIRED / REAL EXECUTION NOT AUTHORIZED`

## Disposition

The reviewed SHA remains unchanged. This response prepares one append-only replacement candidate,
`M1-FREEZE-CANDIDATE-002`, against the complete authority list confirmed by Core. M1 remains
`IN_PROGRESS`; neither this response nor local tests freeze the candidate, authorize real candidate
execution, or substitute for independent Core Designer and Internal Tester approval.

## Finding closure map

| Finding | Replacement implementation | Executable proof |
| --- | --- | --- |
| `M1-FREEZE-001` | `GENERATE.input` and `RESULT.response` now reference exact schemas. Speak requires non-whitespace text. `m1_contract_boundary.py` provides a callable, non-raising P5 normalizer with capability, dotted tool-name, registered tool and public argument-schema checks. It never receives or invokes a handler. | `test_valid_responses_pass_through_callable_normalizer`, `test_p5_invalid_output_table_uses_locked_fallback`, `test_p5_fallback_respects_capability_combinations`, `test_normalizer_emits_no_raw_output_to_logs`, and nested protocol binding tests. |
| `M1-FREEZE-002` | `reasoning-input.schema.json` freezes the Core-facing `ReasoningInput`. `prompt-input.schema.json` is separately identified as the privacy-preserving child projection. The callable projection keeps status, maps missing text to empty text, orders perceptions/capabilities/tools deterministically, reduces pending IDs to count, preserves `name/description/input_schema`, and excludes `request_id`. | Projection equality, shuffle invariance, optional-text equivalence, shape non-interchangeability, pending-ID sentinel absence, and invalid public tool-schema tests. |
| `M1-FREEZE-003` | BUSY rejects only the second request as `GENERATING`; stale `INVALID_REQUEST` is non-terminal. RESULT/CANCELLED/TIMEOUT/GENERATION_FAILED terminate only the active ID and declare `READY`; CANCEL_FAILED/PROTOCOL_ERROR terminate the active ID as `FATAL`. | Active A → rejected B/BUSY → terminal A → next C is valid. Per-code state-table, stale INVALID_REQUEST, duplicate/stale terminal, stale cancel and shutdown-active negatives are executable. |
| `M1-FREEZE-004` | Strict config now carries candidate, pairing revision and platform. The contextual identity validator binds canonical manifest paths, platform-native runtime hash, model hash, actual config hash and READY identity. It rejects traversal/aliases, substitutions and drift; strict schema continues to forbid download, network fallback, fallback model, unknown keys and unfrozen limits. | Exact tuple acceptance plus table negatives for manifest IDs, arbitrary/traversal paths, artifact/config hashes, READY drift and symlink alias; schema negatives cover download/fallback/unknown configuration. |

## Locked replacement packet

- `poc_llm/contracts/m1/reasoning-input.schema.json`
- `poc_llm/contracts/m1/prompt-input.schema.json`
- `poc_llm/contracts/m1/response.schema.json`
- `poc_llm/contracts/m1/protocol-frame.schema.json`
- `poc_llm/contracts/m1/strict-config.schema.json`
- `poc_llm/contracts/m1/contract-fixtures.json`
- `poc_llm/harness/m1_contract_boundary.py`
- `poc_llm/harness/m1_contract_validator.py`
- `poc_llm/tests/gate1/test_m1_contract.py`
- `poc_llm/contracts/m1/m1-contract-lock.json`

The lock authenticates the nine executable artifacts above. Candidate and acquisition manifests stay
separate, including x86 and Pi platform-native runtime artifacts; the contextual validator selects
only the configured platform tuple and creates no Gate 2 evidence credit.

## Deterministic verification

```text
python3 poc_llm/harness/m1_contract_validator.py --self-test
result=PASS; violations=[]; schemas=5; schema_negative_cases=9;
valid_sequences=2; invalid_sequences=3

python3 -m unittest poc_llm.tests.gate1.test_m1_contract -v
Ran 19 tests — OK
```

These are POC Team deterministic observations, not Core approval or hardware evidence. The accepted
Gate 1 Packet Revision 004 remains unchanged. Artifact acquisition, install/download, real x86/Pi
execution, candidate selection, Gate 2A and Gate 2B remain unauthorized.

## Governing review authority

The replacement follows the precedence confirmed in the revision decision: explicit User decisions;
the M4b contract and accepted Gate 1 R4 ACK; Core `docs/arch.md`,
`docs/implement/ch02b_workers.md`, `docs/implement/ch09_action_payload.md`, and
`docs/milestones/M4.md`; delivered `core_llm_m4b_tasks.md`; then the POC M1 milestone, execution plan
and crosswalk where they do not conflict. Core confirmed that no additional standalone development
guide is missing.

## Requested review

Core Designer should review the replacement semantics, then Internal Tester should independently
review the lock, schemas, fixtures, validator, regressions and evidence completeness. Both approvals
are required before M1 can close or M2 preparation can begin.
