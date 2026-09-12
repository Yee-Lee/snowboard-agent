---
requestor: Designer
owner: Tester
status: Resolved
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

1. [`status/current.md`](../../status/current.md) for the active gate and role boundary.
2. [`ch_m4b_llm_production.md`](../../implement/ch_m4b_llm_production.md), especially §§2–11; §11 is the minimum
   verification contract, not an exhaustive list of duplicate test functions.
3. [`protocol.md`](../../protocol.md) §4, [`ch02b_workers.md`](../../implement/ch02b_workers.md) §3,
   [`ch10_config.md`](../../implement/ch10_config.md) §6 and [`model_spec.md`](../../model_spec.md) §6 only for their
   direct M4B mappings.
4. [`m4b_foundation_revision.md`](../../implement/m4b_foundation_revision.md) §§4–8,
   [`test_spec_M4B_foundation.md`](../../test_spec/test_spec_M4B_foundation.md) and
   [`m4b_foundation_node_ids.txt`](../../test_spec/baselines/m4b_foundation_node_ids.txt) only for affected retained
   behavior and immutable regression coverage.
5. Resolved [`AR_impl_M4B_IV`](AR_impl_M4B_IV.md) for the SM-authorized planned-recovery timing boundary.

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

## Tester response — Revised (2026-09-12)

Tester created the current replacement specification at
[`docs/test_spec/test_spec_M4B.md`](../../test_spec/test_spec_M4B.md). This response returns coverage and
traceability only. No production code, executable test, Pi/candidate execution or acceptance result was added.

### Portable group mapping

| §11.1 group | Test-ID range / mapping |
| :--- | :--- |
| 1. listen normalization, envelope, 20/21 and 32/33, controls, no mutation | `M4B-NORM-001` |
| 2. prompt bytes/counts/hashes, grammar, text/end, escapes, spoken length | `M4B-PROMPT-001`, `M4B-SEM-001` |
| 3. fragmented/coalesced S2, prefix and terminal safety | `M4B-S2-001`, `M4B-WIRE-001` |
| 4. MEASURE, equation and one-use binding | `M4B-ADM-001` |
| 5. fresh listen-only prefill tier | `M4B-PREFILL-001` |
| 6. complete canonical outcome matrix | `M4B-OUTCOME-001` |
| 7. same Conversation and sequential replacement | `M4B-CONV-001` |
| 8. memory decisions and SM-authorized recovery | `M4B-MEM-001`, `M4B-REC-001` |
| 9. complete private wire state/proof/PGID matrix | `M4B-WIRE-001` |
| 10. privacy and separate prompt/runtime/memory/timing schemas | `M4B-PRIV-001` |
| 11. retained M1/M2/Foundation/affected-M4A coverage | `M4B-REG-001` |

The portable range is `M4B-NORM-001` through `M4B-REG-001` (13 IDs). Each catalog row fixes the
design/protocol authority and risk, exact permitted target layer, Python/platform matrix, timeout and later
evidence locator. Each case section fixes deterministic stimuli, explicit barriers/fakes, positive assertions
and forbidden side effects.

### Pi and human evidence mapping

| Required evidence | Test ID |
| :--- | :--- |
| artifact/runtime/ABI/profile/prompt/grammar attestation; offline/no fallback | `M4B-PI-ATT-001`, `M4B-PI-RES-001` |
| public V2D2 identity/factual/cannot-see/cannot-tool/end/concise/personality/context cases and human rubric | `M4B-PI-SEM-001` |
| one Product Session through context reject, close-before-open, explicit repeat and next-generation success | `M4B-PI-CONV-001` |
| signed measurement-only run, §5.3 calculation/freeze and separate release-profile rerun | `M4B-PI-MEM-001` |
| WAKE `準備中` preparation with zero active listen/ASR overlap | `M4B-PI-WAKE-001` |
| one-clock Audio+LLM nodes, explicit null/reason, no latency/audible-onset claim | `M4B-PI-TIME-001` |
| network, swap/OOM/kernel/thermal, PGID/orphan/owner and private-content cleanup | `M4B-PI-RES-001` |

The Pi/human range is `M4B-PI-ATT-001` through `M4B-PI-RES-001` (7 IDs). Automated structural status and
human semantic status are separate; missing measurement, required dual-role sign-off, identity, raw series, rubric or null reason
is `Incomplete`/`Fail`, never implicit Pass.

### Immutable baseline comparison

Specification §`M4B-REG-001` fixes the exact fail-closed method: collect the seven approved regression files,
extract and `LC_ALL=C sort -u` node IDs, use `comm -23` against
[`m4b_foundation_node_ids.txt`](../../test_spec/baselines/m4b_foundation_node_ids.txt), assert the immutable baseline
has exactly 99 lines, then require an empty missing-node file. Later evidence must report
`baseline_count=99`, `retained_count=99`, `missing_count=0` and the SHA-256 of baseline/post/missing lists.
Strict-marker JUnit, AST anti-weakening and zero skip/xfail/xpass checks are additional independent gates.

### Tester specification audit

This is a document-level audit only, not product or candidate execution:

- requirement traceability covers all **11/11** portable groups and **7/7** Pi/human evidence bullets;
- independent UTF-8 SHA-256 recomputation of the exact core, personality and no-separator concatenation produced
  `8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec`,
  `57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5` and
  `872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643`, matching design §2.2;
- independent Unicode-category calculation produced `spoken_length=3` for `「你好嗎？」` and `2` for
  `嗨🙂！`; all nine fixed public human utterances normalize to 4–13 code points and therefore remain within
  the 20-codepoint product input boundary before the later exact-token check;
- the retained Foundation baseline is sorted, unique and exactly **99** node IDs; referenced authority paths
  exist and the edited Markdown has no trailing-whitespace error;
- current worktree scope for this round is only the new target specification and this active review.

### Blocking gaps and scope confirmation

Blocking gaps found in the approved design/protocol mapping: **none**.

The specification does not restore legacy action-envelope, fresh-Conversation, fake-prewarm, fixed `8/48/768`,
20-session drift or response-time ceiling semantics. It introduces no product code, executable test, Pi evidence,
candidate claim or acceptance result. All execution rows remain Pending until the later implementation,
exact-candidate and Tester execution gates. Disposition: **Revised; next owner Designer for independent mapping
review.**

## Designer mapping resolution — Resolved (2026-09-12)

Designer independently inspected the target specification and closes `M4B-TEST-COVERAGE`:

- all **11/11** portable groups map to 13 catalog IDs with authority/risk, layer/matrix, timeout, evidence locator,
  deterministic stimulus, explicit barriers, positive assertions and forbidden effects;
- all **7/7** Pi/human evidence groups map to seven exact-SHA IDs and keep execution Pending;
- the canonical outcome matrix, SM-authorized recovery, complete child protocol, privacy schemas and anti-weakening
  boundaries are represented without legacy semantics;
- prompt hashes independently recompute to the three design values, `spoken_length` examples recompute to `3/2`,
  and the immutable baseline is sorted, unique and exactly 99 nodes;
- all referenced relative paths exist and the documentation delta passes `git diff --check`.

No product code, executable tests, target evidence or acceptance result was introduced. No Blocking or Advisory
coverage gap remains. The review is Resolved and archived; the separately gated Developer replacement work may open.
