# Current design status

- Owner: Designer
- Scope: M4B clean rewrite
- State: Foundation verified / USER-directed measurement-authorization removal designed
- Developer entry: **Closed — opens after focused Tester coverage delta**

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
Conversation readiness and the R1/R2/R3/E1 boundary. Foundation implementation design is now
complete; Tester coverage and Designer mapping confirmation are also complete.

Foundation design:
[`m4b_foundation_revision`](../implement/m4b_foundation_revision.md) completed by Designer on
2026-09-10. Coverage authority:
[`test_spec_M4B_foundation`](../test_spec/test_spec_M4B_foundation.md). Coverage review
[`TR_spec_M4B_V`](../reviews/history/TR_spec_M4B_V.md) resolved after Designer Round 3 PASS. Foundation
implementation and independent verification closed on 2026-09-11; cognition/product development remains closed.

## Replacement cognition/product design

Designer completed [`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md) on 2026-09-12; focused
architecture request [`AR_impl_M4B_IV`](../reviews/history/AR_impl_M4B_IV.md) is Resolved. Current decisions are:

- exact Gemma 4 E2B / LiteRT-LM 0.16 product identity with a new `core-m4b-cognition-001` profile;
- V2D2 exact 66-token prompt as one fixed built-in personality, with no user/YAML prompt customization;
- listen-only direct-text projection, exact NFKC/whitespace normalization and `20 codepoints / 32 tokens` input
  boundary;
- constrained JSON `text/end`, 30 spoken-character product rule and S2 safe semantic extraction;
- child-side non-mutating MEASURE plus one-use ticket for exact current-KV/render/output-reserve admission;
- `temperature=0`, `top_p=1`, `128` output reserve and `1024` context; fresh qualifying listen-only prefill
  remains `<=128` while other future projectors need their own tier;
- one real Conversation across turns, explicit context/post-send replacement without replay, and a complete
  application/model speech plus R1/R2/R3/E1 matrix;
- memory pressure ends the session before planned same-key recycle; new thresholds come from a dedicated
  measurement-only harness and are frozen into a release profile, never inherited from legacy `8/48/768`;
- existing Display `WAKE -> 準備中` is the selected nonblocking preparation UX; it adds no state/Fact/model content;
- new private `snowboard.llm/3` protocol and separate prompt, runtime/context, memory and monotonic timing
  dashboards.

Architect resolved the single planned-recovery timing ownership question in `AR_impl_M4B_IV`: existing architecture
already requires SM to authorize planned recovery inside its private post-close convergence phase. Designer aligned
M4B §5.3; `arch.md` required no change. Admission, request-failure cleanup and listen-only composition remain
Designer-owned implementation consistency work, not architecture questions. Independent Reviewer returned PASS
with no Blocking findings in [`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md). Designer adopted A1/A2
and acknowledged A3; `M4B-DESIGN-REVIEW` is Closed. Tester produced the replacement
[`test_spec_M4B`](../test_spec/test_spec_M4B.md); Designer independently confirmed the full mapping and resolved
[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md). `M4B-TEST-COVERAGE` is Closed and
[`CR_M4B_II`](../reviews/history/CR_M4B_II.md) opened and now resolves the Developer replacement package.
Pi/product acceptance remains open work.

Developer subsequently opened Blocking [`IR_dev_M4B_IV`](../reviews/history/IR_dev_M4B_IV.md): measured token-limit R1
had no legal wire transition that both kept the Conversation and invalidated its ticket. Designer confirmed the
gap and selected explicit `DISCARD_TICKET` / `TICKET_DISCARDED`, rejecting next-MEASURE supersession because it
left the old ticket usable between rejection and the next turn. Product and protocol authority now define exact
identity/proof, unchanged Conversation state, private-buffer release and E1 failure convergence. No architecture
or public SM/Event/Fact/response change is involved. Focused Tester request
[`TR_spec_M4B_VII`](../reviews/history/TR_spec_M4B_VII.md) is Resolved after Designer confirmed all 9/9 requirements,
the unchanged 13 portable Test IDs and no Blocking mapping gap. The complete Developer path is open; implementation
and execution evidence remain Pending.

## Other redesign inputs to preserve

### Conversation and admission

- Keep exactly one active Conversation at a time, but allow a single Product Session to replace it
  sequentially after the old Conversation has closed with cleanup proof. Replacement does not by
  itself end the Product Session and never overlaps two claimed Conversations.
- Do not race Conversation open against the initial listen operation. Complete a session-preparation
  readiness barrier before perception starts. The preparation interval may later be hidden with a
  Display or application-owned recorded voice. The replacement design selects the existing `WAKE -> 準備中`
  Display state projection, without a new animation/voice/state; model generation still cannot start before
  Conversation readiness.
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

- Designer retired the superseded M4B design and decision overlays. POC handoffs and immutable
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

Tester independently passed the canonical Linux aarch64 CPython 3.11.16/3.12.14/3.13.15 matrix at
exact candidate `9ffd6e17ad5504d53c7c18799ca4718f69988f7e`: **1005 passed** per minor and zero
Fail/Error/Skip/XFail/XPASS. Matrix SHA-256 is
`2438944bc0ad64f48ae577ca3cd7c2e9ff1c0008174ab8d398459c8293c5fbdb`; profile
`be9005b5426173243ab1306dc24fb969f1371ff86615286ac1405714a98b49f1` and catalog
`bcd92cc2019494f3c854337b761585b79cbddd0f0a7d6b381ff8c35f21c2e001` match authority. Designer
confirmed the B1/B2 corrections are limited to the formal portable gate and found no product-design
deviation or new high-risk regression. Protected inputs are portable-frozen at that SHA.

USER explicitly removed the M4B role-signature workflow. The measurement harness must accept no Designer/Tester
authorization file, reviewer identity or approval timestamp. Controller and child still fail closed on the exact
candidate/profile/harness/target tuple, and the complete raw series deterministically produces the release profile;
a separate clean release rerun remains mandatory. Tester now owns only the focused coverage delta. Developer then
implements the removal once and produces a replacement candidate before direct PM, PR and PH execution.
