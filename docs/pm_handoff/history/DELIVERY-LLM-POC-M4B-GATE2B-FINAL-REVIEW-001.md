# DELIVERY-LLM-POC-M4B-GATE2B-FINAL-REVIEW-001

- **Date**: 2026-08-29
- **From**: Core Designer
- **To**: LLM POC Team (M4b) / PM Team
- **Status**: `RESOLVED — 022/023 ACKNOWLEDGED / FINAL WINNER ACK ISSUED`
- **Refs**: `DELIVERY-022-PM-LLM-POC-GATE2B-PREWARM-LIFECYCLE`, `DELIVERY-023-PM-LLM-POC-GATE2B-MEMORY-PSI-REMOVAL`, `DELIVERY-024-PM-LLM-POC-GATE2B-CLOSURE-GEMMA-WINNER`, `POC-llm-DEL-2026-001-R3`
- **Execution SHA**: `0c75536e6ee99b502c59438989ca852194648946`
- **Execution surface SHA-256**: `22f52d8b8b5b6d0aacbe2959c49441ccee30a0bacb68b9b8fcfc04877c14665a`
- **Formal result**: `G2B-PI-COMBINED-006` / machine P9 `FAIL`, P10B `FAIL`

## Consolidated Core disposition

Core preserves the earlier `DELIVERY-019` and `DELIVERY-021` disposition in
`DELIVERY-LLM-POC-M4B-GATE2A-CLOSURE-ACK-001`: Gemma is the sole model
finalist, the old P2/P8 machine failures remain immutable, and the tested Gate
2A pairing is not retroactively relabelled.

Core acknowledges the User-reviewed Gate 2B Attempt 006 and the User's
governance decision to select `CAND-LRT-G4E2B-MOBILE-R1` as the POC winner under
a known-defect waiver. The waiver does not change P9 or P10B to `PASS`: the
combined PSS slope `5.900893 MiB/session` and late-minus-early median delta
`131.578 MiB` exceeded their frozen limits, while the 20/20 full-chain sessions,
system-used capacity, swap/OOM/thermal/throttle, history boundary and cleanup
observations remain as recorded.

Core is prepared to issue the final-winner ACK after the single Blocking
finding below closes. Until then, the User winner decision is acknowledged but
the R3 manifest is not yet an immutable Core model lock and production
persistent-child implementation remains blocked.

## ACK — DELIVERY-022 pre-warm lifecycle

Core accepts all five requested lifecycle requirements and has integrated them
into `docs/protocol.md`, `docs/implement/ch02b_workers.md` and the M4 gate record:

1. `ENGINE_LOADED` and `INFERENCE_READY` are distinct states;
2. every child start performs one fixed, public, non-sensitive pre-warm through
   the production chat-template/tokenizer/constrained-output path and a
   disposable Conversation before accepting user work;
3. pre-warm is startup availability cost, never hidden in first-request
   latency;
4. rendered input is checked with the model tokenizer against the 128-token
   ceiling, independently of output schema/current-marker validation; and
5. the 15-second generation deadline and two-second terminal-observation-only
   grace are separate; grace cannot turn late generation into success.

The existing wire `READY` name may remain, but its only legal product meaning is
`INFERENCE_READY`. Engine construction alone cannot emit it. Pre-warm output,
Conversation, KV/history and references are discarded before READY.

## ACK — DELIVERY-023 Memory PSI removal

Core accepts Gate 2B packet revision r14 without system-wide Memory PSI. This is
a prospective POC M4B-P9 contract addendum: Attempt 001–005 remain unchanged,
and no missing-PSI result is upgraded. Review of Attempt 006 uses the retained
mandatory gates only: 4 GB `MemTotal - MemAvailable <= 3584 MiB`, `swap=0`,
zero OOM increase, complete owner PSS/RSS/CPU/thread sampling, frozen leak
limits, temperature below 80°C, zero throttling, 20 sessions, history isolation,
reverse shutdown and zero process/ALSA/log-hygiene residue. Sum RSS remains
diagnostic. This does not remove any separately approved Core product
diagnostic or waive Core Gate 3 exact-SHA resource verification.

## M4B-G2B-F01 — Resolved — final delivery identity is immutable

**Contract basis.** `DELIVERY-LLM-POC-M4B-CONTRACT-001` §§6 and 9 require the
POC full SHA and manifest/evidence locators before Core intake; `DELIVERY-024`
and R3 themselves state that their closure/delivery SHA will be supplied only
after commit and push. Candidate identity cannot be a branch head.

**Evidence.** The Git object and 84-test Gate 2 suite are available at execution
SHA `0c75536e6ee99b502c59438989ca852194648946`, but no reachable commit contains
the submitted `DELIVERY-024`, User assessment and `POC-llm-DEL-2026-001-R3` as
an immutable closure set. Their own `closure commit SHA` / `Delivery HEAD`
fields remain pending. Core reproduced:

```text
python3 -m pytest -q poc_llm/tests/gate2
84 passed in 10.96s
```

**Expected / actual.** Expected is one pushed, full 40-character POC closure SHA
whose ancestry includes `0c75536...` and whose committed final-delivery bytes
match the submitted review set. Actual is an intakeable execution surface plus
uncommitted final handoff documents. Without the closure SHA, Core cannot bind
the winner manifest, User waiver and evidence locator to an immutable source or
prove that later branch development did not alter the delivered package.

**Preferred correction.** Create one append-only, docs-only closure commit on
top of `0c75536...` containing the final `DELIVERY-024`, User assessment, R3
winner manifest and required milestone/index closure updates. Do not change the
runner, locks, schemas, configs, artifact identities, sanitized result or any
Attempt 001–006 receipt, and do not rerun Pi execution. Push it and return the
full 40-character SHA plus the three committed paths.

**Minimum re-review conditions.** Core will verify only that:

- `0c75536...` is an ancestor of the supplied closure SHA;
- the closure diff contains documentation/closure records only and no execution
  surface or evidence mutation;
- committed `DELIVERY-024`, User assessment and R3 manifest match this submitted
  handoff; and
- their execution SHA, surface digest, evidence digest, machine FAIL values and
  User waiver remain exact.

No Pi rerun, new benchmark, new product decision or unrelated refactor is
required. Once these checks pass, Core can close M4B-G2B-F01 and issue the final
winner ACK without reopening the already accepted 022/023 decisions.

**Resolution.** `DELIVERY-LLM-POC-M4B-GATE2B-WINNER-HANDOFF-001` supplied
closure content commit `5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae` and provenance descendant
`485bb2a7c07d86a09899f09358c744edd733f875`. Core fetched the pushed objects,
verified both ancestry edges, confirmed closure/addendum diff scope, matched the
three enclosure SHA-256 values and reproduced the Gate 2B lock digest.
`M4B-G2B-F01` is closed by
`DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001`; no execution rerun occurred.

## Downstream Core controls (non-blocking for POC closure)

- R3 became input to `docs/model_spec.md` only after M4B-G2B-F01 closed; no
  model/runtime/config lock was written from an uncommitted manifest.
- `docs/protocol.md` adopts the model-independent pre-warm lifecycle and the
  accepted winner identities supplied by the final ACK.
- Core Gate 3 must define and test a bounded Engine/process recycle policy,
  retaining availability cost and recovery-barrier semantics. It must remeasure
  PSS attribution and `MemAvailable` on the exact product SHA; the POC defect
  waiver grants no product PASS.
- The prior cancellation false-pass advisory remains binding for product tests:
  cancellation outcome, joined worker, single native cancel, Conversation
  discard, healthy replacement and zero unhandled-thread warning must all be
  asserted.
