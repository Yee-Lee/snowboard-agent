---
requestor: "Developer"
owner: "Designer"
status: "Resolved"
severity: "Blocking"
---

# IR_dev_ALPHA_II — Lifecycle continuation against the fixed LLM profile

## Resolution — 2026-10-03

USER explicitly authorized prompt/question changes directly, with empirical results fed back afterward;
the earlier request for preceding Designer document changes is superseded for this repair.
The product prompt now uses `明確要求對話結束時`; its core/personality/combined tokenizer counts are
59/9/68. Profile metadata is consistent with the changed prompt, and startup prompt composition is
compared directly without calculating a text digest. The existing profile ID remains the deployed
family ID for this USER-authorized revision; no model/runtime/schema/admission/API change was made.

USER also authorized reselecting the LLM question. `FX-SHORT-A` now uses the short weekday request
already exercised in diagnosis; actual ASR text is passed unchanged. New fixed PCM was prepared once
for the revised candidate, with old candidate fixtures/evidence preserved.

`ALPHA-L01-DEV-20261003-02` passed on Pi: three Sessions, six Turns, three start Buttons, each cleanup
barrier, graceful shutdown, process/hardware-owner absence, fresh clean-IDLE restart, zero network
attempt/fallback counts and zero aggregate privacy matches. Exit 0. Public result:
`/home/<operator>/alpha-lifecycle-v2-20261003-IUveqU/lifecycle-02/result.json`.
Private logs/observations are under the sibling `private/` directory.

This run uses fixed synthesized PCM through `AudioInput.frames`, real production ASR/LLM/TTS and
ALSA output. It does not test acoustic microphone capture, environmental noise or live spoken input.
Pi focused regression: 179 Pass. Complete non-RPi suite: 1948 Pass / 1 Fail due to absent Git history
in the archive checkout. After providing that history with standard Git commands without changing
product files, the sole affected test passed (1/1). Original failure log is retained. Pi compile and
whitespace checks passed; an independent transfer-boundary comparison found no content difference
for the eight modified source/test/profile files.

B01 is resolved for the revised Lifecycle stimulus and USER-approved prompt. No general model-quality
claim is made; the original arithmetic ASR input still showed a wrong answer in diagnosis. No commit,
formal ALPHA acceptance or revised Performance/Recovery/Quality result is claimed.

Feedback for subsequent authority synchronization: M4B prompt wording/counts/profile metadata and
ALPHA/Test Spec `FX-SHORT-A` must reflect this measured revision. This feedback is not a preceding gate.

## B01 — Fixed first-turn stimulus ends the Session before Turn 2

### Authority and expected behavior

- USER selected Lifecycle repair first on 2026-10-03.
- `docs/milestones/ALPHA.md` §3 and `docs/test_spec/test_spec_ALPHA.md` §3 require three
  two-turn Sessions, one Button per Session, and Turn 2 through KEEP_NEXT.
- `docs/implement/ch_m4b_llm_production.md` §2.2 fixes the exact prompt and profile. It explicitly
  requires every valid model `end=true` to follow END_SESSION; Reasoner must not override or replay it.
  A prompt revision requires an updated profile and semantic evaluation.

### Reproduction and evidence

- Delivered base: `bb5951e`. Target: `<operator>@<pi-host>`, aarch64, product Python 3.13.5.
- Config: `/home/<operator>/m4c-final-dev-20260926-A0dIDk/m4c-product-config.yaml`.
- Unchanged fixture mapping: `/home/<operator>/alpha-dev-20261003-ZSKsbM/fixed-pcm/fixtures.json`.
- Actual run: `ALPHA-L01-DEV-20261003-01`. Public result:
  `/home/<operator>/alpha-dev-20261003-ZSKsbM/lifecycle-01/result.json`.
  Private ASR/terminal observation: the sibling `private/run-observation.json`.
- Command from `/home/<operator>/alpha-dev-20261003-ZSKsbM/repo`:

```bash
/home/<operator>/snowboard-agent-dev/core/.venv/bin/python scripts/run-alpha-pv.py \
  --run lifecycle --run-id ALPHA-L01-DEV-20261003-01 \
  --config /home/<operator>/m4c-final-dev-20260926-A0dIDk/m4c-product-config.yaml \
  --fixtures /home/<operator>/alpha-dev-20261003-ZSKsbM/fixed-pcm/fixtures.json \
  --output /home/<operator>/alpha-dev-20261003-ZSKsbM/lifecycle-01 \
  --watchdog 900 --network-launcher sudo-unshare
```

The recorded output directory is immutable evidence; do not rerun into that directory or retry the
unchanged run for a better answer. Reproduction uses a new output directory and remains diagnostic.

Actual first Turn completed ASR, LLM, TTS and Audio, with schema-valid END_SESSION. The second fixture
remained unconsumed. Result: FAIL / exit 2, SESSION_ENDED_BEFORE_FIXTURES. All five final owner-cleanup
booleans were true. ASR and answer text remain private.

A focused native diagnostic used the same observed ASR text in two fresh Conversations, one streaming
and one synchronous, with the deployed model, schema and original prompt. Both produced `end=true`,
21 decode tokens and 86 first-prefill tokens. Both native renderings contained the exact system prompt
and input. Thus this is not an ALPHA route-observation error or a streaming-only discrepancy.
It does not identify why the model chose that semantic value, or claim every request behaves this way.

One diagnostic prompt proposal clarified that `end` means ending the whole conversation rather than
finishing an answer. It also produced `end=true` on the first ordinary request and on the explicit-end
second request. Its 81 prompt tokens and 101 first-prefill tokens fit the existing budget, but it did
not fix continuation. Raw native diagnostic log, mode 0600:
`/home/<operator>/alpha-lifecycle-fix-20261003-BB29MH/prompt-proposal-diagnostic.log`.
No proposal was adopted into product source, config or profile; this is negative diagnostic evidence,
not Lifecycle or Quality acceptance.

### Follow-up debug requested by USER

Original system prompt and deployed model/sampler were retained. Each isolated question used a fresh
native Conversation. No operator digest check, product transcript rewrite, fixture substitution or
new product gate was added. Only private logs retain original questions and raw responses.

| Diagnostic | Controlled difference | Observed end / semantic validity |
| :--- | :--- | :--- |
| D01 | Observed arithmetic ASR form | JSON: true / valid; unconstrained: true / valid |
| D02 | Written-out arithmetic question | JSON: true / valid; unconstrained: true / valid |
| D03 | Factual question with question mark | JSON: false / valid; unconstrained: non-JSON with an end marker / invalid |
| D04 | Explicit-end request | JSON: true / valid; unconstrained: Markdown-wrapped JSON / invalid |
| D05 | Arithmetic ASR form, question mark instead of period | JSON: true / valid |
| D06 | D03 with period instead of question mark | JSON: true / valid |
| D07 | Different non-arithmetic topic | JSON: false / valid |
| D08 | D03 followed by explicit end in one streaming Conversation | Turn 1 false / valid, Turn 2 true / valid |

All rendered first-turn messages contained the system prompt; their native prefill count was 86.
The arithmetic answers remained incorrect for the observed ASR form with and without JSON constraint;
the written-out arithmetic form answered correctly but still ended. Thus removing JSON constraint
does not repair the observed failure and additionally permits invalid output shapes. The factual
question's punctuation affects end routing under otherwise identical native conditions. D08 proves
the current backend can keep then end a Conversation for one different input, not that all short
requests are reliable or that an ASR-delivered alternative will retain the same punctuation.

Private logs in `/home/<operator>/alpha-lifecycle-fix-20261003-BB29MH/`, mode 0600:

- `question-constraint-debug-01.log`: D01–D04.
- `question-punctuation-debug-02.log`: D05–D07.
- `two-turn-debug-03.log`: D08 using the production streaming runtime path.

This is evidence of input-sensitive model generation, not a proven internal explanation. Alternate
questions were explicitly authorized for debugging only; they do not replace the fixed Lifecycle
PCM or justify transcript punctuation normalization. B01 remains Open.

### USER wording proposal diagnostic

USER proposed replacing only `明確要求結束時` with `明確要求對話結束時` in the original core prompt.
This was evaluated privately on Pi with the same model, original remaining prompt bytes, sampler,
JSON Schema and fresh-Conversation setting. The proposed first-prefill count was 88 (original 86),
within the existing 128-token envelope. No formal prompt/profile was changed.

| Diagnostic | Input category | Original end | Proposed end |
| :--- | :--- | :--- | :--- |
| D09 | Observed arithmetic ASR form | true | false |
| D10 | Written-out arithmetic question | true | false |
| D11 | Factual question with period | true | false |
| D12 | Explicit-end request | true | true |

All four proposed outputs were valid JSON with non-empty speech. The observed arithmetic ASR form
still received an incorrect numerical answer; the other arithmetic and factual questions were answered
correctly. This is promising evidence for the routing correction, not general semantic quality or a
Lifecycle Pass. Same-Conversation and full real-ASR Lifecycle validation of the proposal remain pending.
Private log: `/home/<operator>/alpha-lifecycle-fix-20261003-BB29MH/prompt-user-wording-debug-04.log`.

### Impact and preferred correction

The runner cannot complete the approved two-turn Lifecycle by following the delivered model decision.
Forcing KEEP_NEXT, changing the fixed fixture, replaying the answer or weakening the required Session
sequence would conceal the observed failure.

Please authorize a bounded continuation correction in the LLM prompt/profile authority, with matching
Test Spec routing for that change. Preserve the existing text/end API, model/runtime, Button behavior,
input admission, safe-fragment boundary and legitimate explicit-end route. A wording-only change has
now shown the desired fresh-request routing for USER's specific minimal replacement above; the earlier
longer clarification proposal failed. Adopted product bytes still need same-Conversation and complete
Lifecycle evidence before claiming the fix.
An equivalent correction that preserves these behaviors is acceptable.

### Minimum validation after revision

1. The unchanged first-turn PCM traverses real ASR/LLM and keeps the same Conversation for Turn 2.
2. The unchanged normal-end PCM ends that Conversation through the ordinary product route.
3. The complete Lifecycle executes all three Sessions and six Turns, per-Session barriers, graceful
   shutdown, owner absence, restart, offline observations and the single aggregate privacy scan.
4. Any adopted shared product change receives directly affected portable regression and downstream
   Recovery/Quality/Performance coverage; this does not authorize executing those runs now or claiming
   their earlier evidence applies to revised content.

## Independent runner repair completed

`scripts/alpha_product.py::ProductProbe.normal_session` previously polled the live `_session` pointer.
A fast two-turn Session could finish before that poll, leaving the runner waiting for an already closed
Session. It now observes the durable PCM admission row to obtain the actual Session identity.
The existing actual-controller regression adds a Lifecycle case that completes both Turns before the
start observer runs. Pi driver/oracle/runner suite: 59 Pass, exit 0. Raw log:
`/home/<operator>/alpha-lifecycle-fix-20261003-BB29MH/portable-alpha.log`.
This repairs observation only; it does not resolve B01 or change model routes.

The original finding and diagnostic requests above are retained as decision provenance. They are
superseded by the resolution at the top. Next owner: Developer for the next USER-selected ALPHA run;
Designer/Test Spec owners receive the measured wording/fixture feedback without blocking this repair.
