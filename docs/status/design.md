# Current design status

- Owner: Designer
- Scope: M4B clean rewrite
- State: Foundation verified / constrained-JSON `J` and swap correction retained / #3/#4 finite native contract aligned with POC; Developer runner correction pending
- Developer entry: **Open for narrow #3/#4 finite lifecycle runner correction and affected tests; preserve native JSON/end routing**

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
the unchanged 13 portable Test IDs and no Blocking mapping gap. That Developer path was opened for the then-current
package; the 2026-09-14 constrained-JSON correction below now governs entry.

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
- Do not repeat the old 20-separate-session system-used drift experiment. The earlier plan to keep
  the real model answering until context admission rejects is superseded: POC documented finite
  Conversation reuse, not guaranteed long-fill continuation. Measure the finite native lifecycle
  and actual boundaries through normal application-owned close; exercise the context equation, rejection,
  replacement and following success separately on final Pi bytes with controlled admission snapshots.
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

USER explicitly removed the M4B role-signature workflow. The measurement harness accepts no Designer/Tester
authorization file, reviewer identity or approval timestamp, while controller and child still fail closed on the
exact content/profile/harness/target tuple. [`IR_dev_M4B_V`](../reviews/history/IR_dev_M4B_V.md) then supplied the newer USER decision that PM, PR and PH
are one canonical `PV` stage, not three aliases or sequential gates. Designer accepted B1 and revised product
§§5.3/11.2: independently executable Test IDs produce visible automated, human and measurement sub-results plus
the deterministic threshold estimates under one aggregate `PV` disposition; there is no release rerun or separate
human stage. The estimates do
not mutate profile authority. A later threshold-adoption design/config delta follows the normal pipeline with only
directly affected verification and no default replay of the accepted corpus. The focused seven-ID mapping is now
Resolved in [`TR_spec_M4B_VIII`](../reviews/history/TR_spec_M4B_VIII.md); this is a real acceptance-contract change,
not a role-approval gate.

All earlier PM/PR/PH runs and their partial or complete outputs are obsolete for acceptance. No prior card,
profile, threshold, transcript, status or digest may enter the new `PV`; it begins under a new run ID with newly
empty private/public active evidence roots.

All seven Test IDs are script-executed and independently evaluated. `M4B-PI-SEM-001` additionally requires USER
judgment of the three captured answers. For #1/#3–#7, Developer must inspect every number and output against the
underlying evidence and record a complete reasonableness result; script summaries alone cannot establish product
acceptance. This explicit human evidence requirement adds no role signature, authorization file or extra gate.

Tester corrected all five findings under the earlier script-only authority. Designer then confirmed three
human-only semantic cases, six script-driven Test IDs, independent Test-ID state/evidence, separate commands and
single-case reruns for SEM/WAKE/RES, the core-wired WAKE path under controlled stimuli, eight RES cases and current traceability.
That mapping opened Developer at the time, but the later USER requirement for Developer review of #1/#3–#7
supersedes its result disposition. No product execution or `PV` PASS occurred.

USER confirmed on 2026-09-14 that the Core regex path prevents the real LLM from answering normally. The POC
delivery supports constrained JSON `J` plus S2, but does not support J-via-regex, canonical member order/whitespace
or a GBNF product identity. Designer therefore supersedes the prior `IR_dev_M4B_VI` `char+` direction rather than
changing product semantics to compensate for a regex shortest path. Current §4.1 requires LiteRT-LM
`ResponseFormat.json(response_schema)`, duplicate-aware decoding when raw JSON is exposed, direct validation of an
already-decoded runtime mapping, and exact semantic validation. Legal JSON
member order and insignificant whitespace are equivalent; `end=false` requires normalized non-empty text while
`end=true` permits empty text as delivered by the POC behavior. Prompt/model/sampling/profile ID and unrelated
lifecycle behavior remain unchanged. All regex/GBNF/`char+`-bound implementation and evidence tuples are
superseded. Tester returned the focused mapping across schema/profile/READY identity, JSON lexical equivalence,
raw/decoded terminal paths, S2, empty/end outcomes and real-model answer regressions. Designer confirmed every
direct requirement has an executable case and no portable fake can claim real-model success. That
constrained-JSON mapping remains Resolved.
The constrained-JSON mapping itself remains valid, but Tester reported that its `PV` evidence wording exposed a
separate Designer-authority conflict: prior §11.2 treated #1/#3–#7 as script-only automated results. Designer has
now corrected §11.2 to require script evaluation plus USER #2 verdict and Developer #1/#3–#7 complete
reasonableness review. Tester corrected the detailed mapping with an exact executable command/record schema,
generated complete field/row catalog, private evidence-manifest locator/digest binding, mandatory
`NeedsDeveloperReview`, one per-Test-ID WAKE/RES review after case aggregation, stale-review invalidation and
G07–G10 negative/finalizer matrices. Designer confirmed alignment and temporarily reopened Developer correction
under the then-current schema authority.

The current Developer bytes are not aligned: the review command accepts arbitrary positive counts and commentary,
does not consume an inspection catalog or bind private evidence, writes script `Pass` instead of
`NeedsDeveloperReview`, and can publish review commentary. Separately, mutating the in-memory response-schema
object is accepted under the unchanged canonical digest, decoded-mapping behavior lacks explicit native seam
coverage, and `test_m4b_pv_runner.py` is absent from the canonical portable catalog. These are implementation
findings, not Tester mapping defects; no new-tuple evidence or `PV PASS` exists.

Designer then traced the response schema to POC commit
`4f34226728bafba445aa736e5e8ba24c0e2a69cd` and found a Designer-originated Blocking defect: the prior
correction's minified `oneOf/const/minLength` schema and `642a94...` digest were never the Pi-proven artifact.
The POC used the exact 352-byte `semantic-output-v1.schema.json` file with final LF and digest
`796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`. It deliberately removed native
conditional keywords rejected by LiteRT-LM v0.16 and enforced `text/end` relations in Python. Designer authority
now binds that artifact locator/digest through profile, lock and READY. Current Test Spec P03, P09 and A05
profile-ready still bind the superseded schema, so their schema mapping is open and Developer entry is closed.
The separately corrected Developer-review contract remains valid and must not be discarded during remapping.
Tester revised the exact schema rows on 2026-09-14: P03/P09/A05 profile-ready now bind the locator, 352-byte
deployed artifact and `796c311...` digest; S01 leaves the `text/end` relation to Python; P05/X08 map raw JSON
and direct decoded mapping; Pi ATT/SEM/CONV and traceability map fresh real-model evidence; G07–G10 preserve the
complete Developer-review contract. Designer independently found no Blocking mapping gap and reopened Developer
correction. This transition supplies no source, test, profile, lock, portable, native or `PV PASS` credit.

USER removed the zero-swap-growth verdict on 2026-09-15. Formal POC Gate 2A/2B ran with `swap=0`, and its P9
production-profile surrogate required `SwapTotal=0`; that condition cannot test growth with active zram. The
later efficiency experiment's swap-increase stop was a bounded safeguard, not evidence that any active-zram
delta is product-unsafe. Designer has removed swap-growth-alone E1/laboratory stop/`R02-HEALTH` verdicts from
Product §5.3/§11.2 while preserving swap telemetry, the 512 MiB floor, OOM/kernel fault, throttling,
temperature, sampler/identity and cleanup stops. USER explicitly authorized the focused Test Spec correction:
portable `M02`, Pi MEM `M04-STOPS` and Pi RES `R02-HEALTH` now omit the zero-growth verdict and retain swap
telemetry and all other safety stops; #3 `C01-FIRST` JSON success is unchanged. Developer's two native
`CONV-POC-01/02` attempts remain Incomplete, not `PV` credit. Current affected resource/measurement/PV-runner
workstation tests passed 133/133. Developer then replaced the stale `R02-SWAP-OOM` Pass with OOM-only `R02-OOM`
and exposed setup `SwapTotal`; my affected workstation rerun remains 133/133. Developer reports focused Pi
167/167, but full same-bytes `PV` verification is Pending. The next #3 run with active zram passed the swap
boundary and reached eight real model generations: `C01` and six `C02` fills were non-empty `end=false`, while
`C02-FILL-0007` returned non-empty `end=true`/`END_SESSION` on a non-explicit-end request at KV 376 + 17 + 128
below Engine 1024. No context rejection/replacement occurred, so #3 remains Incomplete. POC V2D2 documented only
two-turn real Conversation reuse, not the long fill assumption. Designer now owns the focused prompt/end-intent
versus scripted-stimulus disposition; Developer must not override the model end route or rerun identical fills to
seek a lucky Pass. Other independent work remains open; this is an upstream correction in the normal pipeline.
Designer corrected the upstream contract after USER challenged the long-fill premise. A schema-valid
`end=true` is a normal model-owned terminal, not inherently a model or Core fault. Product §11.2 and the
USER-authorized Test Spec §5.3/§5.4 now require #3/#4 to execute an independent finite native lifecycle:
first turn, one labelled continuing turn with real Conversation/KV reuse, then normal application-owned close. An
early end before the required continuing turn is non-Pass for that attempt, without override/replay.
Deterministic admission/rejection/notice/replacement/resubmission/following-success behavior remains required
in portable `M4B-CONV-001` `C02`–`C05` on the same final Pi bytes with controlled snapshots, transparently
not credited as native natural context exhaustion. Model-`end=true` final routing is covered by portable
`M4B-OUTCOME-001` `O06`/`O07`, not by an untried native explicit-end prompt. #4 `PV-M4B-ALIGNED-01/MEM-01` actually stopped at the same
old `C02-FILL-0007` after 835 private resource points and correctly kept estimates null; #1/#6 aligned-tuple
Developer reviews are Pass. #3/#4 old attempts remain Incomplete.
Recorded aligned #5 WAKE has four case-level Pi script Passes and Test-ID aggregate/Developer Pass after
inspecting 1,612 fields/573 rows; a transient tool-capacity rejection was retried successfully. USER clarified
that #5 is a controlled-wake **core product wiring** barrier test, not physical voice-wake sensor or physical
Display hardware evidence. Product §11.2 and Test Spec §5.5 now require MockGPIO W01/W03 and
MockWakeWordInputSource W02/W04 only as stimulus endpoints, permit MockDisplay as observer, and keep actual
ButtonInputSource, StateManager, Conversation control, AlsaAudioInput, WhisperCppASR,
DisplayArbiter/StatusBar and both barriers mandatory. W00's existing structured `production_path`/`display`
fields plus trace are sufficient core-wiring description; W04 correctly has no completed barriers. The current
protected-content digest and runner SHA independently match Developer's `FINITE-03` tuple, so no protected runner
edit or product rerun is needed solely to rename W00. Developer designated W02's original card under corrected
mapping; W03/W04 and Test-ID aggregate/review remain pending. The #1/#5/#6
Passes predate the newly changed protected runner/metrics bytes, so they remain development regression evidence
only and do not credit final same-content-digest `PV`. First finite Pi diagnostic
`PV-M4B-FINITE-01/CONV-01` #3 has script plus Developer Pass on two real `end=false` JSON turns, second KV 112
and matching close/cleanup. Independent #4 `MEM-01` has 253 valid samples and script Pass with finite observed
estimates, but Developer withheld Pass because private setup `SwapTotal` was absent. Current runner records
setup `SwapTotal`/swappiness and swap-used endpoints; changed protected bytes make `FINITE-01` non-final.
Corrected finite Pi diagnostic `PV-M4B-FINITE-02` #3 again has script plus Developer Pass; #4 has 270 complete
samples, setup `SwapTotal=2,147,467,264` bytes/swappiness 60 and script Pass with finite estimates. Review
recording failed because its 3,635,477-byte catalog exceeded the former 1 MiB read limit. Developer introduced
a bounded 16 MiB catalog-only reader, but a legal two-turn near-watchdog lifecycle can project about 3,000
samples/~38.5 MiB of catalog at the 0.05 s sampler interval; 16 MiB is still insufficient for complete
every-value review under the former #4 rule. The corrected Product/Test Spec now require full raw-series
preservation and automatic every-point audit, but permit a compact #4 Developer-review catalog of
boundaries/extrema/anomalies/formula and digests; the former 64 MiB manual-catalog expansion request is
superseded. `FINITE-02` is non-final after protected byte changes. The current `FINITE-03` 241-point complete
series can use the existing full catalog plus successful full-series validation/Developer review without a
runner-format edit or remeasurement. Developer should complete that review, the portable controlled C02–C05
proof and same-bytes Pi checks; no native scenario rewrite is indicated.
V2D2 prompt/schema and Core end routing are unchanged.

On `PV-M4B-FINITE-03/RES-R05-A01`, Designer accepts the Pi close→actual StateManager/adapter
fail-closed authorization→old-PGID exit→new READY→real following-turn ledger as indirect matching
three-part close proof under Product §11.2/Test Spec §5.7; missing duplicate raw boolean fields alone do not
block the original card after Developer finishes its other raw review. No protected runner edit is needed.
For R08, Designer independently ran the sanitized Pi-local `validate_semantic(native_output).text` SHA check:
the normalized digest `f4d0c1207e1619f0e4c8864debb428420f36ff8b984607a510e99a133e6c79d6`
matches the captured answer; the differing native raw-text digest is normalization, not an output mismatch.
Designer also resolved #1's orphan duplicate-syscall-capture Test Spec sentence while retaining #7 R01's
actual independent zero-external-attempt trace. The seven-ID Pi final manifest, same protected tuple and
155/155 directly affected Pi context/outcome/measurement/PV-runner tests support M4B `PV` Verify Pass.
Physical wake/display, native context replacement, R06 nested-descendant killing and R07 full product
shutdown remain outside these particular case claims. No commit/push has occurred.
