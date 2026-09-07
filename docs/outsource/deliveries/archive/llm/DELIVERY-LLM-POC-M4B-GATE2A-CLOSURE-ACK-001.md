# DELIVERY-LLM-POC-M4B-GATE2A-CLOSURE-ACK-001

- **Date**: 2026-08-29
- **From**: Core Designer
- **To**: LLM POC Team (M4b) / PM Team
- **Status**: `ACKNOWLEDGED — GATE 2A SELECTION ROUND CLOSED / GATE 2B BLOCKED`
- **Refs**: `DELIVERY-019-PM-LLM-POC-P2-P3-P8-SEMANTICS-ADJUSTMENT`, `DELIVERY-021-PM-LLM-POC-GATE2A-CLOSURE-GEMMA-FINALIST`
- **Reviewed packet**: `G2A-PI-LLM-002`
- **Originally authorized SHA**: `ed7aaca2e187b2287d442d6841e1ab2610b67570`
- **User-authorized replacement execution SHA**: `e2b59fac609e0d768ff3554754363900cbed70a9`
- **Execution surface SHA-256**: `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`
- **POC round-closure commit**: `3c012eb65cc7c8b706fe1c29a3fcafab17696d0f`

## Core decision

Core acknowledges the User-reviewed Gate 2A closure and accepts
`CAND-LRT-G4E2B-MOBILE-R1` (Gemma 4 E2B mobile) as the sole **model
finalist**. Qwen does not advance to the formal Gate 2B path. This closes the
two-candidate Gate 2A execution and selection round; it does not approve the
tested Gemma prompt/configuration as a deliverable baseline, select a final
winner, or authorize physical Gate 2B execution.

Core preserves the delivered machine dispositions without relabelling:

| Candidate | Core disposition |
| :--- | :--- |
| Qwen / `G2A-PI-QWEN-004` | P2 `FAIL` 0/30; P3 `PASS`; P4 remains `Core threshold decision required`; P5 `PASS`; P8 remains `FAIL / DEPENDENCY_LIMITED_BY_P2`. Qwen is excluded, so no P4 waiver or workaround is granted. |
| Gemma / `G2A-PI-GEMMA-002` | P2 `FAIL` 3/30; P3/P4/P5 `PASS`; P8 remains `FAIL / DEPENDENCY_LIMITED_BY_P2`. The model advances; this tested integration configuration does not. |

The sanitized result digests `e0c000df51c26af5c9cc1f1704f13b8b8816b087d64ba596808b4e3be5b4530f`
and `41f1d8e4f74bac25fd83a17fd0bdb776e9cb0bae1c4c04fdc345f378592681e7`
are immutable locators for this round. Core acknowledges the identities and the
User decision relayed by `DELIVERY-021`; the committed closure is intakeable at
the exact POC SHA `3c012eb65cc7c8b706fe1c29a3fcafab17696d0f`.

The replacement execution identity is intentionally distinct from the original
Core authorization. After `ed7aaca...`, the User authorized a deferred,
no-credit Qwen P1.2 observation and the bounded replacement surface that became
`e2b59fac...`; subsequent changes preserved the candidate artifacts, product
configs, prompt catalog, thresholds and repetition counts while recording the
30-second Qwen operational READY observation, private-sysfs offline preflight
and child-owned P5 timeout/health classification. Core accepts `e2b59fac...` as
the execution identity for this closed round. The Qwen P1 ten-second contract
and prior receipts remain unchanged, and P1.2 grants no gate credit.

## P2 / P3 / P8 semantic ACK

Core accepts the `DELIVERY-019` semantic separation:

| Item | Authoritative interpretation |
| :--- | :--- |
| P2 | Qualifies the complete model + runtime/chat template + `PromptBuilder` + generation-config pairing for product integration. Failure rejects that pairing as a baseline, but does not alone rank or reject the bare model artifact. |
| P3 | Independently qualifies deterministic normalization, fallback, allowlist enforcement and log hygiene. It remains mandatory and is not a model-quality ranking. |
| P8 | Qualifies fresh-conversation/history and KV isolation. Proven prior-state leakage is `FAIL`; when current-turn compliance cannot be established because P2 failed, the receipt remains machine `FAIL` and carries `DEPENDENCY_LIMITED_BY_P2`, not an unsupported history-pollution claim. |

The already completed frozen comparison was authorized to finish while this
adjustment was under review. Its receipts must not be rewritten or rerun under a
new label. No schema migration is required for this closed round; a future
schema may encode the causal qualifier directly, but only for a new candidate
cycle.

For model-selection interpretation, this ACK is the controlling addendum to
`DELIVERY-LLM-POC-M4B-CONTRACT-001` §§7.1 and 8. The original P2/P3/P5/P8
mandatory rules continue to govern a deliverable integration configuration and
future Gate 2B entrant; they no longer imply that a bare model artifact cannot
be named a model finalist when its tested pairing fails P2.

## Core integration and Gate 2B entry controls

Before any scored Gate 2B execution, the LLM POC Team must deliver a new Gemma
candidate revision that:

1. versions the complete model/runtime/chat-template/`PromptBuilder`/prompt/
   generation-config identity and uses declared development cases with a
   bounded adaptation budget;
2. freezes that complete surface before scoring and uses a precommitted or
   independently held-out catalog, without replacing this round's evidence;
3. reruns P2/P3/P4/P5/P8 against the revised surface with new immutable
   receipts; P2, P3, P5 and P8 must `PASS`, while P4 must have complete metrics
   and any required Core threshold disposition; and
4. submits the new exact POC SHA, surface digest, artifact/config identities,
   cleanup/offline result and explicit carry-forward versus rerun map for Core
   entry review.

Formal Gate 2B remains additionally gated by all of the following:

- the Accepted Audio final reference is bound exactly to `POC-audio-DEL-2026-001-R1`,
  tag `audio_m4`, SHA `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`, with the required kit;
- Core reviews the new integration-qualified Gemma revision and issues a
  separate Gate 2B entry authorization; and
- the User separately authorizes physical Pi access/execution.

Gate 2B must then execute P9/P10B combined qualification and the required Gate
2A regression on that same frozen revision. Only a later reviewed Gate 2B
closure may produce the final LLM winner ACK and unlock the Core LLM model lock,
production dependency, persistent-child integration and Core Gate 3 work.

POC commits after the exact round-closure SHA are development inputs only. A
branch head, later executable or locally prepared Gate 2B packet grants no Core
intake, gate credit or physical-execution authorization.

## Verification and Core integration advisory

Core reproduced the replacement surface's workstation regression from
`e2b59fac...`:

```text
python3 -m pytest -q poc_llm/tests/gate2 poc_llm/tests/gate1
200 passed, 1 warning in 102.35s
```

The warning is a non-blocking carry-forward advisory and does not reopen the
User-closed Gate 1 or Gate 2A scores. In
`poc_llm/harness/litert_lm_pi_async_child_adapter_v1.py`, `Cancelled` subclasses
`RuntimeError`, but `LiteRtAsyncBackend.generate()` catches `RuntimeError`
before `Cancelled`; the cancellation raised after stream completion is therefore
wrapped as `BackendFailure`. The existing
`test_cancel_once_discards_conversation_and_new_conversation_is_healthy` only
joins the worker and does not assert the first worker outcome, so pytest reports
the unhandled thread exception while the test passes.

The preferred future-revision fix is to catch and re-raise `Cancelled` before
the broader `RuntimeError` branch, capture the worker exception/result in the
test, and assert `Cancelled`, joined worker, exactly one native cancel, discarded
conversation, healthy new conversation and no `PytestUnhandledThreadExceptionWarning`.
Core production code must carry an equivalent regression and must not inherit
this false-pass pattern. This advisory becomes part of the new candidate entry
review but does not require mutation of the preserved Gate 2A evidence.
