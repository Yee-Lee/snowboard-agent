# Current design status

- Owner: Designer
- Scope: M4B clean rewrite
- State: Foundation architecture confirmed; foundation implementation design pending
- Developer entry: **Closed**

## USER-confirmed direction

### 1. Legacy retirement and clean rewrite

- Rewrite M4B design, production implementation and tests. The old M4B behavior is not a
  compatibility target and must not constrain the replacement.
- Temporarily archive the old M4B design and inventory the old production/tests as legacy. Remove
  the temporary archive after the replacement implementation and verification are complete; Git
  history remains the long-term reference.
- Preserve Accepted M4A, POC evidence/provenance and generic EventBus, State Manager, Resource
  Manager, offline/privacy, process-isolation and Level 1/2/3 convergence foundations.
- Cleanup precedes new product design. During cleanup there is no Development Ready claim.

### 2. Confirmed Reasoner behavior and foundation architecture

Gate ID: `M4B-DESIGN-GATE-REASONER-BEHAVIOR`

Status: **CLOSED by USER and Designer / 2026-09-10**.

The matrix must define normal and error outcomes in one place: model versus application-owned
speech, action, `next_perceptions`, `rest`, Conversation `KEEP/REPLACE/CLOSE`, Product Session
continuation/end, event handling and the boundary to existing system-error recovery. It must also
settle final-speak-then-rest, input error, context limit, memory admission and the clean/
replaceable/fatal model-turn split. `UNSUPPORTED_INPUT` is a wiring/contract system error, not a
normal user-retry case.

Architecture gate ID: `M4B-FOUNDATION-ARCH-REVIEW`

Status: **CLOSED by Architect revision, Reviewer PASS and Designer confirmation / 2026-09-10**.

[`AR_impl_M4B_III`](../reviews/history/AR_impl_M4B_III.md) confirms the revised `arch.md` contract for
sequential Conversation replacement, primary action plus post-action routing, pre-perception
Conversation readiness and the R1/R2/R3/E1 boundary. Foundation implementation design may now begin;
Developer entry remains closed until that design and Tester coverage are complete.

## Other redesign inputs to preserve

### Conversation and admission

- Keep exactly one active Conversation at a time, but allow a single Product Session to replace it
  sequentially after the old Conversation has closed with cleanup proof. Replacement does not by
  itself end the Product Session and never overlaps two claimed Conversations.
- Do not race Conversation open against the initial listen operation. Complete a session-preparation
  readiness barrier before perception starts. The preparation interval may later be hidden with a
  Display animation or application-owned recorded voice; the exact UX remains to be designed, and
  model generation still cannot start before Conversation readiness.
- Reuse one real Conversation across normal turns in one Product Session until an explicit
  replacement or session end.
- Admission occurs before `send_message` and uses exact normalization/tokenization, rendered
  incremental tokens, current KV and output reserve. Pre-inference rejection must not mutate the
  Conversation.
- MVA uses explicit Conversation replacement at context limit; future context compaction remains an
  extension point.
- Keep input limit, context limit and system-memory pressure as distinct outcomes.

### Confirmed foundation architecture decisions

- Normal cognition first selects an action, then the application routes the completed action to
  `KEEP_NEXT`, `REPLACE_NEXT` or `END_SESSION`. `LLMResponse` carries `action_kind`,
  `action_payload`, `post_action_route` and `next_perceptions`; `rest` remains a compatibility primary
  kind legal only with `END_SESSION`. Preserve the accepted M1/M2 observable state sequence.
- Non-empty final model speech must complete before rest; it must not create a fake listen turn.
- A post-send model failure that has provable cleanup and a usable Engine is replaceable: use the R2
  Conversation-replacement route within the same Product Session. Repetition alone does not
  automatically escalate to system ERROR; the USER may explicitly reset/end the session via R3.
- Wiring/contract failures and runtime failures without a safe replacement proof use the existing
  system-error recovery boundary instead of R2.

### Development staging

- Do not reopen or restate the Accepted M1/M2 milestones. Before M4B cognition/product development,
  create a separately gated foundation-contract revision for the affected event/outcome, State
  Manager action-exit, rest routing, Conversation replacement and preparation-readiness behavior.
- That revision keeps the external `IDLE -> WAKE -> PERCEPTION -> THINK -> ACTION` state sequence,
  updates affected foundation implementation and regression expectations, and must leave all
  unaffected M1/M2 behavior green. M4B Reasoner development consumes the revised contract rather
  than changing it concurrently.

### Prompt and token dashboard

- V2D2 is the current POC reference, not a permanent product-prompt freeze. Personality
  customization remains design-only and is not yet fixed as presets or arbitrary text.
- The dashboard must separate system-prompt composition from runtime/context allocation.
- The `prefill <= 128` requirement applies only when the turn contains exactly one listen
  perception of at most 20 Unicode codepoints and 32 model tokens. It is not a multimodal or Engine
  context ceiling.
- Future perception projectors, including vision text such as an observation of the current scene,
  require their own exact projection and token budgets. Additional modalities may exceed the
  listen-only 128-token prefill tier, but every admission must remain within the Engine context
  equation.

### Memory and timing evidence

- Existing combined peak `2,382.969 MiB` already includes Conversation allocation; do not add the
  approximately `252.83 MiB` open allocation a second time.
- Do not repeat the old 20-separate-session system-used drift experiment. Measure one Product
  Session across genuine multiple turns until context admission rejects, perform replacement, prove
  a following successful turn and record KV/system memory/LLM PSS before and after replacement and
  session close.
- Separately capture the preparation peak while Conversation open overlaps the selected application
  preparation UX (for example Display animation or recorded voice). The production path does not
  overlap Conversation open with active ASR/listen.
- Do not freeze response-time targets yet. In the integrated vertical slice, record one monotonic
  stage timeline for Conversation ready, ASR final, LLM send, first safe text, LLM terminal, TTS PCM
  ready and Audio first write. Observations are for later review; first write is not claimed as
  audible onset.

### M4B/M4C boundary

- M4B owns the Reasoner contract, Conversation lifecycle, prompt/profile, selected constrained JSON
  plus safe incremental extraction, token/KV/memory admission and the Audio+LLM vertical-slice
  measurements needed to prevent M4C from repeating subsystem breakdown.
- M4C owns final whole-product State Manager/Display composition and exact-product integration
  acceptance; it consumes rather than rediscovers M4B resource and timing facts.

## Cleanup boundary

- Designer now retires the active M4B design and decision overlays. POC handoffs and immutable
  historical evidence remain in place.
- Current M4B production files, product scripts/locks and M4B-specific tests are legacy inventory,
  not design evidence. The cutover inventory is `src/sbd/cognition/{llm,llm_child_protocol,
  prompt_builder,reasoner}.py`, `scripts/m4b_*`, `requirements/m4b/`, `tests/test_m4b_*`,
  `tests/m4b_*` and `tests/fakes/m4b_llm_child.py`. Under the role write matrix, Developer and Tester
  replace/remove their owned files only after this gate and the new design are approved; no item is
  presumed reusable merely because its path survives until cutover.
- Active reviews based on the superseded package cannot release Developer entry. New review scope is
  created only after the replacement design is complete.

## Next Designer work

1. Prepare the separately gated foundation-contract implementation design against the confirmed
   `AR_impl_M4B_III` authority.
2. Route the completed foundation design to Tester for new coverage; keep Developer entry closed
   until both are approved.
3. After the foundation revision verifies, build the remaining replacement M4B design and obtain
   its focused review/coverage before opening cognition/product development.
