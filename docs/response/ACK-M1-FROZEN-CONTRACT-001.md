# M1 Contract Freeze Review Packet 001

- **Review ID**: `M1-FROZEN-CONTRACT-001`
- **Milestone / delivery areas**: M1 / D1, D2, D3, D4, D8
- **Prepared by**: LLM POC Technical Lead
- **Required approvers**: Designer for product semantics; Internal Tester for testability/evidence
- **Date**: 2026-08-20
- **Status**: `FREEZE_CANDIDATE READY FOR SINGLE REVIEW — NOT EXECUTION AUTHORIZATION`

## Purpose and authority

This packet isolates the decisions still required to close M1 before candidate results can influence
the contract. It does not change Core-owned product architecture, authorize artifact acquisition, or
authorize real x86/Pi execution.

The governing inputs are the M4b contract, `core_llm_m4b_tasks.md`, Core's Gate 1 packet R4 ACK,
`docs/arch.md` for the existing product boundary, and the accepted `G1-X86-PI-COMPAT-004` packet.
If this proposal conflicts with a Core decision, the Core decision wins and this packet must be
revised before approval.

## Already fixed by Core

- Output keys are exactly `action_kind`, `action_payload`, and `next_perceptions`; action kinds are
  `speak`, `tool`, and `rest` only.
- `speak` has non-empty text; `tool` has a registered dotted name and object arguments but never
  executes the handler; `rest` has empty payload and no next perceptions.
- `speak` and `tool` require a non-empty, deduplicated subset of registered `listen/read/look`
  capabilities. Invalid/unknown/refusal/empty output is normalized to P5 apology-speak when
  speak+listen are available, otherwise to `rest`; normalization must not raise.
- Each generation is single-turn. A resident model may be reused, but hidden history/KV state may
  not cross operations. Prompt, perception text, raw output, tool payload, credentials, and hidden
  context may not enter normal logs.
- The child contract includes versioned JSON-lines framing, READY, GENERATE, RESULT, CANCEL, ERROR,
  SHUTDOWN, request correlation, bounded timeout, completion/exit proof, one active generation,
  stale/duplicate rejection, force-abort, rebuild barrier, and orphan=0.
- Gate 1 packet, 20-case catalog × 3 repetitions, schemas, selector, no-backfill rule, and Gate 2
  carry-over guard are accepted at `a99009fd5378d987411f37686814c84a1cb2a713`.

## Proposed PromptBuilder boundary

The POC proposes one canonical, single-turn input with no Resource Manager access:

| Field | Proposed rule |
| --- | --- |
| `request_id` | Non-empty correlation ID; never reused while the child is alive. |
| `perceptions` | Ordered current-turn entries containing registered kind, `ok/timeout/error`, and private text only when available. |
| `pending_message_count` | Non-negative payload-free count; no message IDs or content. |
| `capabilities.perceptions` | Deduplicated registered subset of `listen/read/look`. |
| `capabilities.actions` | Deduplicated registered subset of `speak/tool/rest`. |
| `capabilities.tools` | Registered dotted tool names and public argument schema only; no handler or Resource Manager object. |

PromptBuilder must use only this object plus versioned public system instructions and output schema.
It must not read prior-turn messages, hidden model history, credentials, endpoints, or runtime state.

## Proposed wire contract

- Protocol identifier: `snowboard.llm/1`; UTF-8 JSON object per line; no non-protocol stdout.
- Every request-bound GENERATE, RESULT, CANCEL, cancellation outcome, and ERROR carries the same
  `request_id`. READY and SHUTDOWN_ACK are lifecycle frames without a request ID.
- READY identifies protocol version, runtime/model/config identity, and state. GENERATE is accepted
  only in READY. A second GENERATE returns BUSY without changing the active request.
- RESULT is terminal for its request. CANCEL targets only the active request and must yield a
  correlated terminal cancellation or ERROR. Late, duplicate, or unknown request IDs are rejected.
- SHUTDOWN is accepted only after the active request has a terminal outcome; SHUTDOWN_ACK precedes
  clean exit. Parent SIGTERM→bounded wait→SIGKILL→waitpid is recovery control, not a child frame.
- After timeout/cancel, READY is emitted only after short-lived state is released. Crash or
  destructive cleanup requires a new child and READY barrier before another GENERATE.

The Gate 1 fake runner's existing `op` commands remain packet-control inputs behind an adapter and
are not the final wire schema. This keeps the accepted R4 packet unchanged while requiring any
candidate adapter to expose the frozen final frames before Gate 2 credit is possible.

## Strict-config freeze candidate

Strict config will reject unknown keys, floating versions, runtime download, network fallback,
implicit model fallback, and paths not supplied by the approved manifest. The complete candidate is
`poc_llm/contracts/m1/strict-config.schema.json`:

| Field | Freeze candidate | Basis |
| --- | --- | --- |
| Protocol/driver | `snowboard.llm/1`; `litert_lm` only | M4b runtime/protocol boundary |
| Input/output | 128 / 16 tokens | Existing `G1-CANDIDATE-PREFLIGHT-001` frozen pairing envelope |
| Sampling/threads | temperature 0.0; top-p 1.0; 4 threads | Deterministic comparison on Pi 5 |
| Final child READY | 10,000ms | Gate 2 P1; separate from Gate 1's 180s compatibility model-load bound |
| Generate/cancel | 15,000ms / 500ms | P5 example frozen as candidate; P6 mandatory bound |
| TERM/KILL/rebuild | 2,000ms / 1,000ms / 10,000ms | Bounded Level 2/recovery proposal |
| Identity/paths | Absolute approved paths plus runtime/model SHA-256 | Manifest-bound; values vary only by approved pairing |
| Download/fallback | Runtime download false; network fallback false; fallback model null | Offline and strict-config requirements |

## Frozen candidate artifacts and deterministic proof

- `poc_llm/contracts/m1/m1-contract-lock.json` authenticates PromptBuilder input, response, protocol,
  strict-config, fixtures, validator, and tests.
- `m1_contract_validator.py --self-test` validates Draft 2020-12 schemas, lock checksums, capability
  context, 7 schema-negative cases, 2 valid lifecycle sequences, and 3 invalid lifecycle sequences.
- `test_m1_contract` adds stale cancel/result, duplicate terminal, unregistered tool, and protocol
  stdout contamination regressions. Current Developer observation: `5/5 OK`; contract self-test
  `PASS`, violations empty. This is not Internal Tester confirmation.

## Single approval decision and exit effect

The review is deliberately one packet, not a sequence of piecemeal questions:

- Designer: approve this exact PromptBuilder, response/P5, protocol/adapter boundary, and strict-config
  candidate as frozen; or reject once with the specific clauses and replacement decisions.
- Internal Tester: approve the locked schemas/fixtures/validator/tests and evidence completeness as
  testable; or reject once with specific missing deterministic cases.
- Both reviewers confirm the M4b contract and delivered Core task boundary are the governing M1
  checklist; if another formal checklist exists, it must be supplied in the same review.

Until both approvals are recorded, this packet does not close M1 and M1 remains `IN_PROGRESS`.
Approval freezes the locked candidate but still does not authorize artifact acquisition or real
x86/Pi execution.
