# Core Designer → PM → LLM POC Team: M1 Freeze Candidate Revision 001

- **Delivery ID**: `DELIVERY-LLM-POC-M1-FREEZE-REVISION-001`
- **In response to**: `DELIVERY-004-PM-LLM-POC-M1-FREEZE-CANDIDATE`
- **Reviewed POC branch / exact commit**: `llm` / `0b5a92872f8a695b145b389168111420cd2592c5`
- **From**: Core Team Designer
- **To**: PM and LLM POC Team
- **Date**: 2026-08-20
- **Status**: `REVISION REQUIRED — EXACT CANDIDATE NOT FROZEN / REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `No`

## 1. Consolidated disposition

Core Designer rejects the exact M1 Freeze Candidate at
`0b5a92872f8a695b145b389168111420cd2592c5`. The checksum lock is authentic and the submitted
self-tests pass, but the packet contains contract false-pass paths and a protocol state-machine
contradiction. Freezing it would allow a child adapter to pass while violating the existing Core
PromptBuilder, product response/P5, request-correlation and strict identity boundaries.

The reviewed SHA remains immutable. Submit all findings below in one append-only replacement
candidate and provide its new full SHA. This decision does not withdraw the accepted Gate 1 Packet
Revision 004 and does not reopen its selector, platform split, no-backfill or evidence carry-over
rules.

The Internal Tester gate is **not reached for this rejected exact candidate**. The Tester must
independently review the replacement candidate's locked schemas, fixtures, validator, negative
regressions and evidence completeness. No Tester approval is inferred by this Designer review.

## 2. Verification record

The review used the clean POC repository at the exact submitted SHA. The POC worktree remained
unchanged. The Core copy and POC copy of the M4b contract both have SHA-256
`afd69a09091021d221ceb80ae84bb01d9de69098571ef71d3d91b0f5a7aa130f`.

| Check | Result |
| :--- | :--- |
| Seven artifacts vs `m1-contract-lock.json` | **PASS — all SHA-256 values matched** |
| `python3 -m unittest -v poc_llm.tests.gate1.test_m1_contract` | **5/5 OK** |
| `python3 poc_llm/harness/m1_contract_validator.py --self-test` | **PASS — zero reported violations** |
| `python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet_v4` | **9/9 OK** |
| `python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet` | **6/6 OK** |

The two packet suites were rerun from a temporary copy because the source POC repository was kept
read-only. These green results establish regression stability, not correctness of the new freeze
candidate; the targeted reproductions below demonstrate the uncovered false-pass paths.

## 3. Blocking findings and replacement decisions

### `M1-FREEZE-001` — Product response and P5 boundary is not enforced

**Contract basis:** M4b contract P2/P3; `docs/implement/ch09_action_payload.md` §§3–8;
`core_llm_m4b_tasks.md` `CORE-LLM-02`.

**Evidence:** `response.schema.json` accepts a speak payload whose text is only spaces, although the
Core contract requires `text.strip()` to be non-empty. The protocol schema also accepts
`GENERATE.input={}` and `RESULT.response={}` because both are unconstrained objects. The current
unknown-tool test only proves that a name is absent from a Python set; it does not invoke a
contract validator that rejects the response. No locked reference normalizer executes invalid,
empty or refused raw model output and proves the specified P5 result.

Minimal reproduction at the reviewed SHA returned:

```text
blank_speak_schema_valid= True
unbound_generate_schema_valid= True
unbound_result_schema_valid= True
```

**Expected / actual:** the frozen child boundary must reject or normalize every product-invalid
value before it becomes `LLMResponse`; currently several invalid values pass the advertised schema
and the P5 fixtures are static examples rather than proof of normalization.

**Required replacement:**

1. Bind `GENERATE.input` to the frozen generate-input schema and `RESULT.response` to the exact
   normalized-response schema; do not retain open `{ "type": "object" }` placeholders.
2. Align speak validation with Core's non-blank rule and tool-name validation with the exact Core
   dotted-name rule. Add contextual validation for available action/perception kinds, registered
   tool name and the tool's public argument schema.
3. Lock a callable reference normalizer or equivalent deterministic adapter boundary. It must
   transform empty output, refusal, malformed JSON, unknown action/tool and invalid tool arguments
   into apology-speak only when `speak` and `listen` are available, otherwise canonical rest; it
   must never raise or execute a handler.
4. Add table-driven regressions for whitespace speak, non-object/wrong-key payloads, unavailable
   action/perception, unknown tool, invalid arguments, fallback capability combinations and
   prompt/raw-output/payload log sentinels.

**Minimum acceptance:** every invalid case is rejected or produces the exact P5 fallback through
the real locked validator/normalizer path; no handler call, sensitive log entry or invalid terminal
response is produced. Valid speak/tool/rest cases continue to pass.

### `M1-FREEZE-002` — PromptBuilder candidate conflates product input and child request envelope

**Contract basis:** `docs/arch.md` §2.7; `docs/implement/ch02b_workers.md` §3.1;
`docs/implement/ch09_action_payload.md` §5; `CORE-LLM-02`.

**Evidence:** the frozen schema calls itself the PromptBuilder input but replaces Core's
payload-free `pending_message_ids` input with only `pending_message_count`, adds the protocol
`request_id`, and exposes tool definitions as `name + arguments_schema`. The current Core
PromptBuilder boundary receives pending IDs and emits count plus opaque IDs; the sealed public tool
view is `name + description + input_schema`. No mapping document establishes that the submitted
object is a post-PromptBuilder child projection rather than a replacement for the product input.

**Expected / actual:** a POC projection may be narrower, but it may not silently redefine the exact
Core PromptBuilder contract that this handoff asks Core to freeze.

**Required replacement:** freeze the two layers separately. Keep a Core-facing mapping that follows
the existing `ReasoningInput` and sealed tool-schema view. Define the request-correlated child
`GENERATE` envelope as a separate wire object. If the child receives only count and no opaque IDs,
record that as a privacy-preserving projection after PromptBuilder, not as a replacement product
input. Specify deterministic ordering, optional/empty text behavior and the exact conversion at the
adapter boundary.

**Minimum acceptance:** fixtures prove that perception completion order cannot change the canonical
prompt, pending payload never crosses the boundary, the product tool view maps without renaming
ambiguity, and `request_id` is used only for wire correlation. No Core composition-root or
StateManager change is required.

### `M1-FREEZE-003` — BUSY cannot be represented without corrupting the active request

**Contract basis:** M4b contract P1/P5/P6; `CORE-LLM-03/04`; submitted packet's rule that a second
`GENERATE` returns `BUSY` without changing the active request.

**Evidence:** `validate_sequence()` treats every `ERROR` as a terminal outcome for the active
request. A `BUSY` error correlated to the rejected second request is therefore rejected because it
does not match the first active request. Correlating it to the first request would instead terminate
the wrong operation. The reproduced valid-intent sequence reports:

```text
frame 2: terminal frame does not match active request
```

The schema's `ERROR.state` also permits only `READY` or `FATAL`, so it cannot report that the child
remains generating the first request.

**Required replacement:** define an explicit per-code transition table. The preferred encoding is
`ERROR(code="BUSY", request_id=<rejected-id>, state="GENERATING")` as a non-terminal rejection that
leaves the original active ID unchanged. `INVALID_REQUEST` for an unknown/stale ID must likewise
state whether it is non-terminal. Only a terminal code correlated to the active request may clear
that request. Make terminal readiness explicit and consistent: either terminal frames carry the
post-cleanup state or a separate READY frame is required, but the prose, schema and validator must
use one rule.

**Minimum acceptance:** one valid sequence proves active A → rejected B/BUSY → terminal A → next
generation; negative cases prove BUSY cannot terminate A, stale/duplicate terminal frames cannot
clear a current request, shutdown cannot occur while active, and timeout/cancel cleanup reaches the
declared readiness state.

### `M1-FREEZE-004` — Strict config does not bind approved manifest identity

**Contract basis:** M4b contract P1/P11/P12 and §4 Gate 1 identity rule; `CORE-LLM-03`; accepted
Gate 1 Packet Revision 004 identity separation.

**Evidence:** `strict-config.schema.json` checks only that runtime/model paths are absolute and hashes
look like SHA-256. Replacing both approved paths with arbitrary absolute paths still validates:

```text
arbitrary_absolute_paths_schema_valid= True
```

The M1 validator performs no contextual equality check against the approved candidate/acquisition
manifest and no READY-to-config identity comparison. Therefore the claim "approved absolute paths
and SHA-256 identity" is not currently enforced.

**Required replacement:** retain the strict schema for shape, then add a locked contextual identity
validator that binds candidate/pairing revision, canonical runtime/model path, platform-native
artifact hashes, config hash and READY identity to the approved manifests. It must reject unknown
keys, path traversal/aliasing, path/hash mismatch, unapproved artifact substitution, runtime/model
fallback and any READY identity drift. Do not merge x86 and Pi platform-native acquisition hashes
or permit Gate 1 identity to become Gate 2 credit.

**Minimum acceptance:** table-driven negatives cover arbitrary absolute paths, canonical-path or
symlink alias mismatch, wrong artifact/config hash, fallback/network/download enablement and READY
identity mismatch. Each fails before candidate execution; cleanup/evidence rules from Revision 004
remain unchanged.

## 4. Governing M1 checklist decision

The delivered M4b contract and `core_llm_m4b_tasks.md` are confirmed as governing M1 inputs, but the
task document is a scope summary rather than the sole normative schema. The complete authority set
for the replacement review is:

1. explicit User decisions;
2. `DELIVERY-LLM-POC-M4B-CONTRACT-001` and accepted Gate 1 Packet R4 ACK;
3. Core `docs/arch.md`, `docs/implement/ch02b_workers.md`,
   `docs/implement/ch09_action_payload.md`, and `docs/milestones/M4.md`;
4. `core_llm_m4b_tasks.md` as the delivered Core work boundary; and
5. the POC M1 milestone, authoritative execution plan and traceability crosswalk where they do not
   conflict with the Core documents above.

No additional standalone development guide is missing. If a lower-authority POC document conflicts
with this list, the Core contract and product design win. The replacement candidate should cite
this list directly so that M1 can close without another checklist-discovery round.

## 5. Authorization boundary and next state

- M1 remains `IN_PROGRESS`; this exact candidate is not frozen and must not be tagged complete.
- Preserve `0b5a92872f8a695b145b389168111420cd2592c5`; append a new candidate commit.
- Return one new handoff with the replacement full SHA, updated lock and all four finding IDs mapped
  to files/tests.
- Internal Tester independently reviews that replacement packet after Designer semantics are
  corrected; both approvals are required before M2 preparation.
- Artifact acquisition/download/install, real x86 execution, Pi access/transfer/network switching,
  candidate selection and Gate 2A/2B remain unauthorized.

