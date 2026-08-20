# Core Designer → PM → LLM POC Team: M1 Freeze Candidate Revision 002

- **Delivery ID**: `DELIVERY-LLM-POC-M1-FREEZE-REVISION-002`
- **In response to**: `DELIVERY-005-PM-LLM-POC-M1-FREEZE-CANDIDATE-R2`
- **Reviewed POC branch / exact commit**: `llm` / `93b34c14d5ee0f767ee16dd0fbbbb72e18775760`
- **Rejected predecessor**: `0b5a92872f8a695b145b389168111420cd2592c5`
- **From**: Core Team Designer
- **To**: PM and LLM POC Team
- **Date**: 2026-08-20
- **Status**: `REVISION REQUIRED — R2 NOT FROZEN / REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `No`

## 1. Consolidated disposition

Core Designer confirms that replacement candidate R2 is append-only and closes the product/child
input separation in `M1-FREEZE-002`. The response/P5, protocol and identity corrections are largely
implemented, all nine locked artifact hashes match, and all submitted deterministic suites pass.

The exact candidate `93b34c14d5ee0f767ee16dd0fbbbb72e18775760` is nevertheless **not approved for freeze** because
one protocol false-pass remains: the lifecycle validator accepts frames after FATAL. The correction
is localized below with an implementation and regression skeleton. This review does not reopen the
accepted Gate 1 Packet Revision 004 or add a new product requirement.

The Internal Tester gate is **not reached for this Designer-rejected exact candidate**. Internal
Tester must independently review the next replacement lock and deterministic evidence after these
semantic gaps close.

## 2. Finding closure matrix

| Original finding | R2 disposition | Reason |
| :--- | :--- | :--- |
| `M1-FREEZE-001` | **Closed** | Exact wire refs, blank speak, callable P5, capability/tool/argument checks and log hygiene are present. Core-owned invalid public schema metadata remains a startup/registration concern, not a model-output freeze blocker. |
| `M1-FREEZE-002` | **Closed** | Core `ReasoningInput` and privacy-preserving child projection are distinct, deterministic and mapped with the exact public tool fields; pending IDs and wire request ID remain in their proper boundaries. |
| `M1-FREEZE-003` | **Partially closed / Blocking remains** | BUSY correlation and active-request preservation are fixed; the state machine still accepts frames after a FATAL terminal state. |
| `M1-FREEZE-004` | **Closed** | Candidate/platform/path/artifact/READY tuple checks are present. Raw config-file hashing remains owned by the already accepted Gate 1 runner/authenticated-manifest path and is not duplicated as a new M1 freeze gate. |

## 3. Verification record

Review was run from an exported temporary snapshot of exact candidate SHA `93b34c14...`; the source
POC worktree remained clean and unchanged.

| Check | Result |
| :--- | :--- |
| Nine files vs `m1-contract-lock.json` | **PASS — all SHA-256 values matched** |
| `m1_contract_validator.py --self-test` | **PASS — zero reported violations** |
| Replacement contract suite | **19/19 OK** |
| Combined replacement + Gate 1 R4/R3 suites | **34/34 OK** |

The green suites establish retained behavior but do not cover the single reproduction below.

## 4. Single remaining Blocking finding

### `M1-FREEZE-003-R2` — FATAL is not terminal in the lifecycle validator

**Contract basis:** M4b contract P7; `CORE-LLM-04`; Revision 001 `M1-FREEZE-003` required one
consistent per-code transition table with fatal/terminal readiness semantics.

**Evidence / reproduction:** after an active request returns `PROTOCOL_ERROR/FATAL`, the validator
sets `fatal=True` but only checks that flag for later `GENERATE` and `SHUTDOWN`. A later
`INVALID_REQUEST/READY` frame is accepted and the whole sequence reports no error:

```text
post_fatal_sequence_errors= []
```

**Expected / actual:** FATAL ends the child wire stream. No READY, ERROR, RESULT, CANCEL or other
child frame is legal afterward. R2 currently permits the state to appear healthy again without a
new child, waitpid proof or recovery READY barrier.

**Direct correction:** in `poc_llm/harness/m1_contract_validator.py::validate_sequence`, insert the
guard immediately after schema validation and before `frame_type = frame["type"]`:

```python
        if fatal:
            errors.append(f"frame {index}: frame after FATAL")
            continue
```

Keep FATAL explicitly scoped as a child-wire terminal outcome only: it does not itself prove parent
`force_abort()`, terminate/kill/waitpid, outer completion or RM rebuild. Those P7 proofs remain
external Gate 2 evidence and are not claimed by this M1 schema.

**Direct regression skeleton:** add one table-driven test beside the existing lifecycle tests. Build
a valid prefix `READY → GENERATE → ERROR(PROTOCOL_ERROR, FATAL)`, append each of `READY`, `ERROR`,
`RESULT`, `CANCEL`, `SHUTDOWN`, and `SHUTDOWN_ACK`, then assert every sequence returns an error
containing `frame after FATAL`. After changing validator/tests, recompute their SHA-256 values in
`m1-contract-lock.json`; otherwise the self-test must correctly fail on lock mismatch. The original
FATAL frame may close the child wire sequence, but cannot count as Level 2 completion or authorize
another generation.

**Verified completion commands:** Core applied the exact guard and table case to a temporary export
of `93b34c14...`, updated only the validator/tests lock entries, and confirmed:

```text
python3 poc_llm/harness/m1_contract_validator.py --self-test
result=PASS; violations=[]

python3 -m unittest -v poc_llm.tests.gate1.test_m1_contract
Ran 20 tests — OK

python3 -m unittest -q \
  poc_llm.tests.gate1.test_m1_contract \
  poc_llm.tests.gate1.test_gate1_packet_v4 \
  poc_llm.tests.gate1.test_gate1_packet
Ran 35 tests — OK
```

All six injected trailing frame types were rejected with `frame after FATAL`. This proves the
preferred correction is directly applicable and closes the finding without changing schema,
fixtures, boundary semantics, Gate 1 packet or product architecture.

## 5. Non-blocking ownership notes

- Public tool-schema resolver hardening is advisory for future Core product integration. The current
  M1 fixed registered tool schema is self-contained and valid; invalid Core-owned registration data
  is not model output and does not expand this freeze gate.
- Exact raw config bytes and checksum authentication remain required by the accepted Gate 1 runner
  and manifest. R2's contextual validator checks the semantic tuple; it is not required to duplicate
  the runner's artifact-reader responsibility.

## 6. Next state and authorization boundary

- Preserve `93b34c14d5ee0f767ee16dd0fbbbb72e18775760`; append one replacement candidate.
- Re-review scope is locked to the `M1-FREEZE-003-R2` guard and its direct regression. Findings 001,
  002 and 004 stay closed unless that localized patch directly regresses them. No new preference or
  previously discoverable edge case may be promoted to Blocking in the next review.
- M1 remains `IN_PROGRESS`; no M1 tag or freeze is authorized.
- Artifact acquisition/download/install, real Ubuntu execution, Pi access/transfer/network
  switching/execution, candidate selection and Gate 2A/2B remain unauthorized.
