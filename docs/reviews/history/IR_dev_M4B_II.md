---
requestor: "Developer"
owner: "Designer"
status: "Resolved"
severity: "Blocking"
---

# IR_dev_M4B_II — Core generic renderer cannot satisfy the fixed marker gate

## Decision requested

Please reconcile the approved Core generic renderer/schema with the mandatory
Pi current-marker gate. Developer cannot make `M4B-OUT-001`, `M4B-HIST-001`, or
`M4B-RES-001` pass without changing a Designer-owned contract, weakening the
test, or adding prohibited post-hoc output repair.

## Contract basis

`docs/implement/ch_m4b_llm_production.md` §3.2 fixes all of the following:

- `_render_prompt()` is the short generic M1 renderer with the fixed public
  pre-warm digest;
- the Core `speak` constrained schema requires only nonblank text and does not
  bind a marker-specific pattern;
- scored examples, hidden fields, request retry, output repair, and literal
  injection are prohibited;
- the Gate 2B marker harness and Core general `speak/tool/rest` renderer are a
  product delta that must be revalidated at Gate 3.

`docs/test_spec/test_spec_M4.md` §M4B-REC-001 and §M4B-RES-001 simultaneously
require 20 accepted Pi sessions, each containing the current marker exactly
once, with no forbidden or prior marker.

## Sanitized Pi reproduction

- Base candidate: `274b2dbd88e97c267b48d723a08a6d594c040ada` with an uncommitted
  source-only Developer overlay; the candidate checkout remained clean.
- Debug run: `m4b-274b2db-20260831-debug-m4bonly01`, Linux aarch64,
  CPython 3.13.5, loopback-only network namespace.
- The real accepted LiteRT-LM/Gemma product completed startup, pre-warm, one
  structured inference, exact response-shape validation, and bounded cleanup.
- Session 1 returned a valid `speak` response, but
  `current_marker_count=0` for `M4BC0001`; expected count was exactly one.
  No private transcript or model response is copied into this review.
- Pytest result: `1 failed` at the current-marker assertion. Repeating or
  selecting a better result is prohibited and was not attempted.
- The same working tree passed the complete local non-RPi regression:
  `678 passed`, `29 target-only deselected`, exit code 0. The remaining failure
  is therefore isolated to the real selected product and Pi marker oracle.

Separate syscall evidence also proved the preceding lifecycle fixes: the LLM
child read `SHUTDOWN` and wrote `SHUTDOWN_ACK` immediately. The earlier apparent
shutdown timeout was cleanup masking a replacement timeout; Developer corrected
the timeout scope so full pre-spawn authentication remains outside the fixed
10-second child READY window. The quality failure above is now the unmasked root
blocker.

## Gate 2B comparison

At immutable POC execution SHA
`0c75536e6ee99b502c59438989ca852194648946`,
`poc_llm/harness/litert_lm_gate2b_child_adapter_v2.py` does not rely on the
model following an unconstrained free-text marker request. It parses structured
`REQUIRED_LITERAL` / `FORBIDDEN_LITERAL` fields and adds the required literal as
a JSON-Schema `pattern` for `action_payload.text`. Core §3.2 deliberately omits
that narrow surface. Therefore Gate 2B PASS does not prove the current Core
marker oracle.

## Required Designer disposition

Please select and fully specify one contract-level resolution:

1. **Structured literal constraint:** add an explicit, bounded, generic
   required/forbidden-literal field to the canonical reasoning input and wire
   schema, define validation and privacy rules, and authorize deterministic
   constrained-schema projection. This must not parse arbitrary user prose,
   hard-code scored markers, or repair model output.
2. **Revised Core renderer/profile:** authorize a versioned generic prompt or
   other product-profile change that demonstrably passes a separate development
   catalog, then define the affected lock/digest and P2/P4/P5/P8/Gate 3
   requalification scope.
3. **Revised acceptance claim:** remove the exact marker requirement from the
   Core general-renderer gate and replace it with a Designer/Tester-approved
   history-isolation oracle. This requires a corresponding Tester-owned spec
   revision and may not relabel the historical Gate 2B result.
4. **Product no-go/reselection:** retain the existing generic contract and
   declare the selected model/pairing unsuitable for Core Gate 3.

## Work blocked while open

- Pi debug completion at 8/8 and any formal target PASS;
- a new provisional candidate commit or portable/evidence rerun;
- Developer completion and Tester handoff for M4b.

Portable regressions and the already identified lifecycle/ALSA fixes may remain
as uncommitted work. Developer will not weaken the marker assertion, add retries,
copy scored literals into the prompt, or claim evidence completion while this
review is Open.

## Designer disposition（2026-09-01）

**Disposition: Revised — contract mismatch confirmed；Option 3 revised Core acceptance claim selected.**

The sanitized Pi result is sufficient to prove the mismatch: the selected product returned a wire/schema-valid
nonblank `speak` result while the generic renderer and dynamic schema had no contractual mechanism requiring
`M4BC0001`. Requiring that literal anyway would make Gate 3 stricter than `ch_m4b` §3.2, and would incorrectly
transfer the Gate 2B harness-only `REQUIRED_LITERAL` pattern into the Core product contract.

This does not revise or relabel the immutable Gate 2B result. It revises only the Core product-delta oracle.
Gate 2B current/forbidden/prior-marker receipts remain historical POC evidence.

### Selected contract

- Core `ReasoningInput`, `snowboard.llm/1`, `_render_prompt()` and `_build_response_schema()` remain unchanged.
  No required/forbidden-literal field, marker-specific regex, scored literal, retry or post-hoc repair is authorized.
- `M4B-OUT-001` uses a bounded semantic intent catalog. Every Pi case must pass the exact response schema and
  Reasoner validator and match the current input's expected `action_kind`, current tool name where applicable,
  and current capability/`next_perceptions` allowlist. `speak.text` is required to be nonblank, not to echo a literal.
- `M4B-HIST-001` combines three independent proofs per transition: a current-turn semantic positive oracle,
  fresh-Conversation/create-close evidence, and absence of prior action/tool/perception/canary state. A missing
  current literal is not a failure; wrong current action/schema/allowlist, reused Conversation, or prior-state hit is.
- `M4B-RES-001` keeps all 20 sessions, three generations, r14 4/64 resource gates, offline identity, cleanup and
  Audio→LLM→TTS terminal assertions. Functional validity becomes 20/20 schema + Reasoner + current-input
  binding + nonblank speak + exact current next-perception + TTS terminal, with no marker count.

Designer-owned authorities were revised in `docs/implement/ch_m4b_llm_production.md`, `docs/protocol.md`,
`docs/model_spec.md`, `docs/implement/ch02b_workers.md` and `docs/milestones/M4.md`. Tester-owned acceptance
details are intentionally not edited by Designer; `TR_spec_M4B_III` now requests the localized spec/card revision.

### Preferred Developer correction after `TR_spec_M4B_III` is Resolved

Modify only the acceptance/catalog surfaces directly coupled to the obsolete oracle:

1. Replace `requirements/m4b/gate3-product-catalog.json::resource_marker_profile` with a bounded generic
   session/intent profile that carries no required or forbidden literal.
2. In `tests/m4b_target_cases.py::test_m4b_exact_product_gate3_cards`, remove current-marker generation/counting;
   assert current semantic binding and Reasoner validation for the 20 combined sessions and the three intent cases.
3. Update `scripts/m4b_target_metrics.py::load_gate3_catalog`, `scripts/candidate_gate.py` M4B card schemas and
   their regressions in `tests/test_m4b_res_001.py` / `tests/test_candidate_gate.py` to the revised evidence fields.
4. Retain injected prior-state leaks and wrong current action/tool/next-perception as fail-closed regressions.
   Keep raw perception/model text out of result cards and logs.

Do not modify the production renderer/schema, Reasoner normalization, product lock/runtime/model/config,
pre-warm prompt/digest, token/sampling/deadline profile, lifecycle/recovery/resource implementation, or M4a
Accepted contract for this finding.

### Minimum regression

- positive OUT: fixed `speak`, `tool`, `rest` semantic cases each match the current expected action; tool name and
  next perceptions come only from current capabilities; Reasoner validation count equals accepted case count;
- positive HIST: five transitions each have current semantic PASS, distinct fresh Conversation/create-close proof,
  prior-state hits zero, stable PID/load within a generation and only expected attempt-8/16 generation switches;
- positive RES: 20/20 combined sessions produce schema-valid nonblank `speak`, exact current singleton
  `next_perceptions`, Reasoner PASS and successful TTS terminal while all existing resource/cleanup gates remain;
- negative: a schema-valid response with the prior tool/action/perception/canary fails; wrong current action or
  current allowlist fails; reused/missing Conversation close fails; P5/invalid response cannot count as accepted;
- contract guard: a schema-valid, semantically current response with no requested marker passes, and catalog/wire/
  response schema contain no required/forbidden-literal field or marker pattern.

Developer fast-loop work and the existing uncommitted lifecycle/ALSA fixes may continue. Until
`TR_spec_M4B_III` is Resolved, no provisional candidate, formal portable matrix, Pi Gate 3 run or acceptance
evidence may be created. Please confirm this boundary; an equivalent implementation satisfying the same behavior
and evidence is acceptable.

## Developer confirmation（2026-09-01）

**Disposition: Resolved — Option 3 revised Core acceptance claim accepted.**

Developer確認修訂後契約可實作，且沒有改動或放寬production renderer、`ReasoningInput`、
`snowboard.llm/1`、dynamic response schema、Reasoner authority、runtime/model/config identity、
pre-warm digest、recovery/resource thresholds或M4a Accepted boundary。以current-turn exact action／
capability／tool／`next_perceptions`正向綁定，加上fresh Conversation/create-close與prior-state absence，
可在不要求arbitrary literal echo的前提下驗證Core generic product的語意正確性與history isolation。

Developer將只修改Designer列出的acceptance/catalog/card direct surfaces，保留20-session、三generation、
r14 4/64、offline、Audio→LLM→TTS terminal、privacy與zero-residue gates；不加入marker field、regex、
prompt injection、retry或output repair。`TR_spec_M4B_III`仍是獨立Blocking gate：其未Resolved前僅進行
fast-loop準備，不建立candidate、不執行Pi Gate 3或正式evidence。
