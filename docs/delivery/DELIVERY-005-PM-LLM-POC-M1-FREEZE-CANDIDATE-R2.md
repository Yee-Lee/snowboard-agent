# LLM POC M1 Freeze Replacement Candidate R2

- **Delivery ID**: `DELIVERY-005-PM-LLM-POC-M1-FREEZE-CANDIDATE-R2`
- **In response to**: `DELIVERY-LLM-POC-M1-FREEZE-REVISION-001`
- **From / via**: LLM POC Team / User-authorized Agent courier
- **To**: Core Designer and Internal Tester
- **Branch**: `llm`
- **Exact replacement candidate SHA**: `93b34c14d5ee0f767ee16dd0fbbbb72e18775760`
- **Rejected predecessor SHA**: `0b5a92872f8a695b145b389168111420cd2592c5`
- **Date**: 2026-08-20
- **Status**: `REPLACEMENT READY FOR INDEPENDENT REVIEW / REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `No product composition-root or StateManager change`

## Review target

Please review the `llm` branch at the exact replacement SHA above. The predecessor remains immutable;
the replacement is an append-only candidate containing all four requested corrections in one commit.
This delivery record is intentionally committed after the review target so that it can state the full
candidate SHA without an impossible Git self-reference. It does not alter the candidate artifacts.

Core Designer approval of corrected semantics and independent Internal Tester approval of the locked
schemas, fixtures, validator, regressions and evidence completeness are both required. M1 remains
`IN_PROGRESS`; no tag has been created.

## Finding-to-proof map

| Finding | Candidate files | Locked executable review |
| --- | --- | --- |
| `M1-FREEZE-001` | `response.schema.json`, `protocol-frame.schema.json`, `m1_contract_boundary.py` | Callable P5 normalizer rejects/normalizes blank, malformed, wrong-shape, refused, unavailable, unknown-tool and invalid-argument cases; protocol binds GENERATE/RESULT; valid speak/tool/rest pass; log sentinels stay absent; no handler surface exists. |
| `M1-FREEZE-002` | `reasoning-input.schema.json`, `prompt-input.schema.json`, `m1_contract_boundary.py` | Tests prove distinct Core and child shapes, deterministic order, missing/empty text equivalence, pending-ID privacy projection, exact public tool fields and wire-only `request_id`. |
| `M1-FREEZE-003` | `protocol-frame.schema.json`, `contract-fixtures.json`, `m1_contract_validator.py` | Active A → rejected B/BUSY → terminal A → next C passes; BUSY/stale INVALID_REQUEST stay non-terminal; terminal code states, duplicate/stale IDs, timeout/cancel readiness and active shutdown are checked. |
| `M1-FREEZE-004` | `strict-config.schema.json`, `m1_contract_boundary.py`, `contract-fixtures.json` | Candidate/revision/platform, canonical manifest paths, platform-native hashes, actual config hash and READY tuple are bound; arbitrary/traversal/symlink paths, substitutions, drift, download/network/fallback and unknown config fail before execution. |

Detailed technical mapping:
`docs/response/RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-001.md`.

## Lock and verification record

- Contract lock: `poc_llm/contracts/m1/m1-contract-lock.json`
- Contract ID: `M1-FREEZE-CANDIDATE-002`
- Lock SHA-256: `cf061a6610d52e777cc850c4f3d13885d5860ec46c4f85e1120c1979bd06095a`
- Locked executable artifacts: 9
- Draft 2020-12 schemas: 5
- Schema-negative cases: 9
- Valid/invalid frozen fixture sequences: 2 / 3

```text
python3 poc_llm/harness/m1_contract_validator.py --self-test
PASS; violations=[]

python3 -m unittest -q poc_llm.tests.gate1.test_m1_contract
Ran 19 tests — OK

python3 -m unittest -q \
  poc_llm.tests.gate1.test_m1_contract \
  poc_llm.tests.gate1.test_gate1_packet_v4 \
  poc_llm.tests.gate1.test_gate1_packet
Ran 34 tests — OK
```

The 34-test combined total is 19 replacement regressions plus the retained 9 Revision 004 and 6
Revision 003 Gate 1 regressions. These are deterministic POC Team observations only, not hardware
evidence or reviewer approval.

## Authority and authorization boundary

The candidate uses the complete authority set confirmed by Core: explicit User decisions; M4b
contract and accepted Gate 1 R4 ACK; Core `docs/arch.md`, `docs/implement/ch02b_workers.md`,
`docs/implement/ch09_action_payload.md`, and `docs/milestones/M4.md`; delivered
`core_llm_m4b_tasks.md`; then non-conflicting POC milestone/plan/crosswalk material. No additional
standalone guide is missing.

This handoff does not authorize artifact acquisition, download/install, real Ubuntu execution, Pi
access/transfer/network switching/execution, candidate selection, Gate 2A or Gate 2B. The accepted
Gate 1 Packet Revision 004 is unchanged and grants no Gate 2 evidence credit.

## Requested disposition

Return one consolidated review against the exact candidate SHA:

1. Core Designer: approve the corrected product/child boundary, P5, protocol and identity semantics,
   or return all remaining semantic findings together.
2. Internal Tester: independently approve the lock and executable evidence completeness, or return
   all remaining deterministic gaps together.

Only after both approvals may the POC Team evaluate the remaining M1 exit conditions.
