---
requestor: Designer
owner: Tester
status: Open
severity: Blocking
target: docs/test_spec/test_spec_M4B.md
---

# TR_spec_M4B_VI — replacement cognition/product coverage

- Date: 2026-09-12
- Blocking gate: `M4B-TEST-COVERAGE`
- Activation: **Active — test-spec authoring only**
- Candidate SHA: not required for this specification round; product execution remains deferred

## Request boundary

Create a new current `docs/test_spec/test_spec_M4B.md` for the clean M4B replacement. This round
defines coverage and traceability; it does not implement production/tests, run a product candidate, collect Pi
evidence or reopen Accepted M4A.

The retired M4B action-envelope, fresh-Conversation, fake-prewarm, fixed `8/48/768`, forced 20-session drift and
2s/3s response-threshold semantics are not compatibility targets. Existing `TR_spec_M4B_I`–`IV`, archived
`test_spec_M4B_R1` and legacy tests cannot be copied or used to release this gate. The verified Foundation spec and
immutable node-ID baseline are regression inputs only.

## Authority to read

1. [`status/current.md`](../status/current.md) for the active gate and role boundary.
2. [`ch_m4b_llm_production.md`](../implement/ch_m4b_llm_production.md), especially §§2–11; §11 is the minimum
   verification contract, not an exhaustive list of duplicate test functions.
3. [`protocol.md`](../protocol.md) §4, [`ch02b_workers.md`](../implement/ch02b_workers.md) §3,
   [`ch10_config.md`](../implement/ch10_config.md) §6 and [`model_spec.md`](../model_spec.md) §6 only for their
   direct M4B mappings.
4. [`m4b_foundation_revision.md`](../implement/m4b_foundation_revision.md) §§4–8,
   [`test_spec_M4B_foundation.md`](../test_spec/test_spec_M4B_foundation.md) and
   [`m4b_foundation_node_ids.txt`](../test_spec/baselines/m4b_foundation_node_ids.txt) only for affected retained
   behavior and immutable regression coverage.
5. Resolved [`AR_impl_M4B_IV`](history/AR_impl_M4B_IV.md) for the SM-authorized planned-recovery timing boundary.

Do not read legacy design/test archives as background. If an exact historical Test ID is needed to prove retained
coverage, locate only that ID from the immutable baseline.

## Required specification form

For every Test ID, record:

- exact design/protocol clause and risk;
- target layer (`portable unit`, `portable integration`, `portable subprocess`, `Pi measurement`, or `Pi human`);
- deterministic stimulus, fixture/fake and explicit synchronization barrier;
- observable assertions, including forbidden calls/state/artifacts;
- applicable Python/platform matrix and timeout;
- evidence/result locator required later, without claiming a result in this round.

Table-driven cases may cover multiple boundaries when every row remains traceable. Test/function counts are not an
acceptance criterion.

## Blocking portable coverage

The new spec must independently map all eleven groups in product design §11.1:

1. Exact listen normalization and `20/21` codepoint plus `32/33` direct-token boundaries; unsupported envelope,
   control-character and no-mutation cases.
2. Exact prompt bytes, tokenizer counts and three hashes; fixed personality, grammar, all `text/end` combinations,
   escapes and the 30-spoken-character rule. Pin examples: `「你好嗎？」` has `spoken_length=3` because CJK
   punctuation is category `P` and excluded; `嗨🙂！` has `spoken_length=2` because the emoji symbol counts while
   punctuation does not.
3. Fragmented/coalesced UTF-8 and JSON S2 extraction; prefix proof, invalid ordering, late/duplicate terminal and
   no unsafe partial speech.
4. Non-mutating MEASURE and the exact context equation boundaries; one-use ticket, stale revision, input digest,
   generation identity and GENERATE-only mutation.
5. Fresh listen-only `runtime_prefill <= 128` with explicit proof that it is neither a multimodal allowance nor the
   `1024` context ceiling.
6. Every canonical §6 outcome row, including speech ownership, KEEP/REPLACE/END, final-speak-then-rest, empty end,
   input/context/memory distinctions, replaceable post-send failure and repeated R2 without count escalation.
7. Same Conversation across normal turns; pre-mutation context rejection; close-before-open replacement, following
   successful turn, no replay, and unchanged Product Session/monotonic turn identity.
8. Memory allow/notice/silent decisions with injected release-profile thresholds and sampler faults. Planned
   recovery coverage must prove all of the following:
   - Adapter atomically marks `RECYCLE_PENDING` but cleanup proof alone produces zero `ScheduleRecovery` calls.
   - SM authorizes one same-key recovery only after primary action/rest terminal and matching close/cleanup proof.
   - SM does not clear session tracking, resume wake admission or return to `IDLE` before RM READY.
   - RM failure/timeout reaches Level 3, including no-next-request/no-ticket-waiter supervision.
   - Legacy recycle keys and fixed `8/48/768` policy are rejected.
9. Complete `snowboard.llm/3` READY/OPEN/MEASURE/GENERATE/SAFE_TEXT/RESULT/REQUEST_FAILED/CANCEL/CLOSE/SHUTDOWN
   state, identity and proof matrix; bounded PGID cleanup and a successful new child after planned recovery.
10. Private-data redaction plus separate prompt/runtime/context, memory and monotonic-timing schemas, including
    explicit null/reason handling.
11. Retention of every affected M1/M2/Foundation/M4A regression without delete, skip or xfail substitution. The
    immutable Foundation node-ID baseline must report retained/missing counts; do not rerun unrelated Accepted
    M4A-only acceptance rows.

All portable async/concurrency tests use explicit events/barriers and bounded waits, never correctness sleeps.
Deterministic fakes may prove control semantics but cannot claim real-model response quality, memory or timing.

## Blocking Pi and human-evidence plan

The spec must define, but must not execute in this round, the product-design §11.2 exact-SHA procedure:

- artifact/runtime/ABI/profile/prompt/grammar attestation and offline/no-fallback proof;
- the public V2D2 identity, factual, cannot-see, cannot-tool, positive/negative end, concise/personality and genuine
  context-dependent follow-up cases, with a human rubric and sanitized evidence fields;
- one genuine multi-turn Product Session through context rejection, close-before-open replacement, repeat request
  and a successful new-generation turn;
- signed measurement-only memory harness, the §5.3 threshold calculation/freeze review, then a separate normal
  release-profile rerun;
- Conversation preparation overlapping only the existing WAKE `準備中` Display projection, never active ASR/listen;
- one-clock Audio+LLM timeline with explicit null/reason nodes and no latency PASS ceiling or audible-onset claim;
- no-network, swap/OOM/kernel/thermal, orphan/owner-leak and post-close private-content checks.

The plan must separate automated structural PASS from human semantic PASS and mark missing/invalid measurements as
Incomplete/Fail rather than silently passing.

## Required Tester disposition

Tester creates the target spec, then updates this review to `Revised` with:

1. a Test-ID range mapped to each portable group 1–11 above;
2. a case/evidence mapping for every Pi/human bullet;
3. the exact immutable-baseline comparison method;
4. any Blocking gap with authority, location, expected/actual and minimum correction;
5. confirmation that no legacy semantics, product code, executable test or acceptance result was introduced.

Designer will independently verify the mapping. Only Designer may then mark this review `Resolved`, move it to
history, close `M4B-TEST-COVERAGE` and decide whether the cognition/product Developer entry can open.
