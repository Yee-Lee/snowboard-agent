# ALPHA Test Spec — Voice-only product convergence

## 1. Authority and purpose

This specification maps [`../milestones/ALPHA.md`](../milestones/ALPHA.md) into five Raspberry Pi
product areas: Lifecycle (L), Performance (P), Recovery (R), Quality (Q) and Manual (M). It does not reopen M4／M4C qualification and does not add product capability.

| Test ID | Product risk answered | Required disposition |
| :--- | :--- | :--- |
| `ALPHA-L01-LIFECYCLE` | Repeated use, cleanup, shutdown or restart leaves stale work or owners | `PASS`／`FAIL` |
| `ALPHA-P01-PERFORMANCE` | First-response delay is misattributed or automatic and human observations disagree | Valid PN／PH, explained correspondence and explicit improvement disposition; §4.5–§4.10 |
| `ALPHA-R01-LLM-RECOVERY` | A real LLM child failure leaks old output or cannot return the product to service | `PASS`／`FAIL` |
| `ALPHA-Q-RUN-01-QUALITY` | The complete voice path produces unusable or misleading answers | `PASS`／`FAIL`／`NEEDS_USER_DECISION` |
| `M` (Alpha Manual) | Fixed PCM misses real microphone, audible output, Display or operation failures | `PASS`／`FAIL`／`PENDING` |

L, P, R and Q are independent runs; PN／PH are cases inside P, not another product area or top-level
Test ID. M is a separately identified free-conversation segment and may share a human session with PH.
The six quality cases belong to one quality run, not six fresh-start runs. Offline and privacy stay inside L.
This revision synchronizes the 2026-10-11 design; it records no new execution PASS and changes no historical evidence.

### 1.1 Value and risk pruning

Each retained assertion observes a user-visible product failure: stale cross-session state, incomplete owner cleanup,
unexplained first-response delay, failed recovery, unusable speech output, or real-input／operation failure.
Two fresh-App blocks per PN／PH mode are retained solely to distinguish process-first from Session-first
and follow-up delay. Expanded timing prevents optimizing the wrong interval; conditional 06 must answer
one named confound. Revised Q separates basic usability from brittle text matching; M covers actual hearing
and free use. No extra repetitions, fixed-string oracle or generic evidence checklist earns acceptance credit.
The following add no ALPHA decision value and must not be collected as acceptance work:

- soak, repeated quality attempts, latency ceilings, resource／thermal trends or capacity research;
- hardware, dependency, model, config, license, checksum, manifest or source digest revalidation;
- full fault matrices, abnormal-shutdown matrices or repetition of Accepted M4 rows;
- authorization, identity proof, candidate freeze assertion, generic close-proof or extra role sign-off.

An observed OOM, throttling, hang or other concrete product failure is recorded as the failing symptom and routed
for focused diagnosis; it does not expand this spec into general system research.

## 2. Common execution contract

### 2.1 Target and run isolation

All final runs execute on the Raspberry Pi using the delivered network-disabled product configuration, production
ASR／LLM／TTS／Audio backends and the delivered external launcher. A run may use runner-controlled fixed PCM as
the voice source, but may not bypass ASR, inject an ASR transcript, synthesize a terminal `LLMResponse`, mutate
State Manager state, or replace production TTS／Audio with a null backend.

The candidate locator and target facts are delivery metadata, not Test IDs or PASS assertions. Lifecycle,
Performance, Recovery and Quality must each begin with no product App process left from a previous run. PN／PH use the fresh-block
boundaries in §4.5; M sharing PH uses a separately labeled free-use segment in §6A. A runner
precondition failure makes that run `INVALID`; it must be corrected before the single valid execution begins.

Every command has a finite runner watchdog recorded before execution. The watchdog only prevents an unbounded
harness hang; it is not a response-time requirement and its duration is not reported as a product threshold. Once
the first product stimulus is admitted, timeout, runner crash, fixture substitution or lost required observation
ends the run as `FAIL`／`INVALID` as specified below; the runner may not retry the case to obtain a better result.

### 2.2 Fixed fixtures

Before execution, the runner resolves these local PCM identities. Exact paths may be deployment-specific, but the
mapping and audio bytes stay unchanged within the applicable experiment／final verification.
Retained P uses its existing fixture binding; revised Q uses fixture revision `Q-20261011`, fixed before
execution. PN and PH use question revision `PNPH-20261011`; PH uses real speech, not PCM playback.
Public evidence records only the fixture ID, never transcript or PCM content.

| Fixture ID | Private spoken content / use |
| :--- | :--- |
| `FX-SHORT-A` | Eligible short request for L／R: 「一個星期有幾天？」 |
| `FX-SHORT-B` | Eligible matched short request: 「一個星期有幾天？」; used by both P02 and P03 |
| `FX-FOLLOW-UP` | Session A follow-up: 「請再簡短回答一次。」 |
| `FX-MULTI-FRAGMENT` | 「請列出三個滑雪安全重點。」 |
| `FX-NORMAL-END` | 「現在請結束對話。」 |
| `FX-Q01` … `FX-Q06-T2` | Exact quality stimuli in §6.2; Q05 and Q06 each have two ordered turn fixtures |

The runner must prove each PCM reached the real ASR path and received one ASR terminal. It may privately compare
the decoded text where needed to diagnose fixture eligibility, but public evidence stores only
`asr_terminal=true|false` and a stable failure code.

### 2.3 Observation and privacy boundary

Runner instrumentation may observe existing product events, private controls, process ownership and monotonic
timestamps. It must not publish a product Event or Fact, add a state transition, change fragment boundaries, or
hold an owner that the product would otherwise release.

Raw transcript, prompt, model output and audio remain private and local to the Pi. They may be viewed only where
needed for the one semantic judgment or focused diagnosis. Public evidence is limited to Test／case ID, fixture
ID, booleans, counts, stable codes, process identity equality／difference booleans, monotonic timing nodes and
sanitized reasons. Credentials are never evidence.

## 3. `ALPHA-L01-LIFECYCLE`

### 3.1 Setup and steps

1. Disable external networking and start the App with the delivered launcher.
2. Wait for every required resource to report READY and for App state `IDLE`. Before the first button stimulus,
   record that no Conversation exists, Display Status is `待命`, and Display Main is empty.
3. In the same App process, execute Sessions 1–3. Each Session has exactly two turns:
   - Turn 1: new Button trigger, `FX-SHORT-A`, real ASR → LLM → legal terminal route → required TTS／Audio;
   - Turn 2: `FX-NORMAL-END`; if the legal terminal contains speakable text, drain TTS／Audio before REST;
     otherwise take the legal direct-REST route.
4. After every Session, wait for its complete cleanup barrier before admitting the next Button trigger.
5. After Session 3 cleanup, request graceful shutdown through the formal product operation.
6. After process exit and owner checks, invoke the same launcher again. Wait for a new process to reach clean
   `IDLE`; do not start another Session. Gracefully stop it so the run finalizer can release the target.
7. Scan the complete public output of this run once for privacy violations and report aggregate counts.

### 3.2 Per-turn and per-session acceptance

Across the three Sessions and all six turns:

- exactly one new Button stimulus starts each Session, for three admitted Session-start Buttons total;
- each Session's two fixed PCM stimuli are consumed once by the intended current turn through real ASR and LLM;
  Turn 2 follows the existing `KEEP_NEXT` transition without another Button;
- the terminal route is schema-valid and either completes required TTS／Audio or takes the legal direct-REST path;
- no old-operation normal terminal is accepted after cancellation or convergence.

At each of the three Session barriers, all of the following must be true before the next Session is admitted:

- active Conversation closed exactly once;
- session-owned task count, streaming-control count, queue depth and in-flight operation count are all zero;
- no late audio, stale Fact, provisional fragment or previous-Session content enters the next Session;
- Display is `IDLE`／`待命` with empty Main;
- the persistent backend PID set equals the set recorded after initial READY; a new Session adds no backend PID.

After the first shutdown:

- launcher-observed App exit code is `0`;
- App and every product child PID no longer exist;
- ALSA holder count, Display fullscreen-owner count and other product hardware-owner count are zero;
- restart creates a different App PID, creates no Conversation before input, and reaches `IDLE`／`待命` with
  empty Main.

Across the whole run:

- external network-attempt count and network-fallback count are zero;
- the one aggregate public-evidence scan reports zero transcript, prompt, raw model output, credential and full
  audio-payload matches.

Any missing requirement is `FAIL`; assertions may not be averaged across Sessions. Public evidence contains one
run result plus three per-Session result objects and six per-turn objective result objects.

## 4. `ALPHA-P01-PERFORMANCE`

### 4.1 Setup and controlled sequence

This retained P01–P05 mode keeps its definitions and historical results. It is not automatically rerun for
ALPHA.P; new work follows §§4.5–4.10. Preserve its input delivery behavior when adding PN pacing.
Start one fresh App process with the production configuration and a fixed instrumentation setting. Execute exactly
this order in one run:

1. `P01-STARTUP`: process start through App `IDLE`.
2. Session A Turn 1, `P02-FIRST-TURN`, using `FX-SHORT-B`.
3. Session A Turn 2, `P04-FOLLOW-UP`, using `FX-FOLLOW-UP`.
4. Close Session A with `FX-NORMAL-END` and wait for cleanup; the close turn is not a performance case.
5. Session B Turn 1, `P03-WARM-SESSION`, using the same `FX-SHORT-B` bytes as P02.
6. Session B Turn 2, `P05-STREAMING`, using `FX-MULTI-FRAGMENT`.
7. Close Session B with `FX-NORMAL-END`, wait for cleanup, then gracefully stop the App.

### 4.2 Required monotonic nodes

All timestamps use one monotonic clock domain and preserve the observed sample; no average, best-of selection,
outlier deletion or substituted fixture is allowed.

| Case | Required ordered nodes and values |
| :--- | :--- |
| `P01-STARTUP` | process start; config complete; READY time for each required resource; App `IDLE` |
| `P02-FIRST-TURN` | Conversation ready; speech end; ASR final; LLM send; first safe text; LLM terminal; TTS first PCM; Audio first positive write; Audio complete |
| `P04-FOLLOW-UP` | previous action complete; next perception start; ASR final; LLM send; first safe text; LLM terminal; input-token count; context-token count; Audio complete |
| `P03-WARM-SESSION` | new Conversation ready; the same ASR→Audio node set as P02; engine reuse boolean and child-identity reuse boolean |
| `P05-STREAMING` | for each admitted fragment: admission, queue-entry depth, TTS start, TTS first PCM, Audio segment start／complete; plus queue wait, LLM terminal and final drain |

The report derives non-negative adjacent durations and an end-to-end duration for each case. It does not invent a
node for a stage that did not occur: a genuinely absent optional node is recorded as `not_applicable` with its
stable reason; an unobserved required node makes the baseline `INVALID`.

### 4.3 Valid baseline verdict

`VALID_BASELINE` requires:

- P01–P05 each completed its specified product path once and every required node is present and causally ordered;
- P02 and P03 used the same resolved `FX-SHORT-B` input through the same measurement configuration; the runner
  reuses that one fixture binding and does not perform a recurring content-digest check;
- both Session close turns completed cleanup but are excluded from performance values;
- failed or invalid observations, if any, remain present in the report rather than being dropped;
- the report names the largest directly measured end-to-end stage for each case, and identifies a cross-case
  product bottleneck only when the observations support one.

There is no numerical latency PASS threshold. A complete baseline may be `VALID_BASELINE` even when no optimization
is justified. Missing nodes, altered fixtures, mixed clocks, instrumentation-caused behavior, a failed product
path or selective sample removal produces `INVALID`.

### 4.4 Retained P improvement boundary

Retained P01–P05 observations remain locatable and unchanged. They do not replace the new paired baseline.
This round's sole bounded improvement, if justified, uses §§4.5–4.10; the old optional-improvement paragraph
does not create a second work item or a requirement to rerun all retained P cases.

### 4.5 PN／PH fixtures, admission and exact schedule

Use the delivered `19d9ca2` product path as the baseline, retaining interruption／restart／stop repair.
Use the same installed composition, source, profile, model, runtime, prompts, schema, admission and collector
for the two modes. Operator supplies private deployment paths once at experiment entry; no recurring digest
or model／config revalidation is part of a case. Instrumentation is identified separately from product changes
and is identical before／after. Required pairs and fixture bindings are:

| Pair | Stimulus／state | Required observations |
| :--- | :--- | :--- |
| `PN01`／`PH01` | Fresh App through READY／IDLE | Process start, config complete, each required resource READY, IDLE; startup prework and prior-inference booleans |
| `PN02`／`PH02` | Session A T1, `FX-SHORT-B`「一個星期有幾天？」 | First frame, speech end where measured, ASR endpoint／final, Conversation create／ready, complete LLM boundaries, first TTS PCM, first positive Audio write／complete／final drain |
| `PN04`／`PH04` | Same Conversation A T2, `FX-FOLLOW-UP`「請再簡短回答一次。」 | Previous action complete, next perception start; same ASR→Audio boundaries and input／context／output counts |
| `PN03`／`PH03` | New Conversation B T1, same `FX-SHORT-B` | Same boundaries as 02; engine／child reuse and Conversation-difference booleans |
| `PN05`／`PH05` | Same Conversation B T2, `FX-MULTI-FRAGMENT`「請列出三個滑雪安全重點。」 | Complete turn timing plus each fragment admission, queue-entry depth／wait, TTS batch start／first PCM, Audio segment start／complete, LLM terminal and final drain |

Before consists of exactly two fresh-App blocks per mode: PN block 1／2 and PH block 1／2. Each block:

1. Start via the installed composition; collect from process start and before the first request. Wait for READY／IDLE (01).
2. Use the formal Session-start Button callback (PN) or physical Button (PH); deliver the fixed short question (02).
3. After actual product completion and KEEP_NEXT, deliver the fixed follow-up in the same Conversation (04).
4. Deliver `FX-NORMAL-END`「現在請結束對話。」; wait for actual cleanup.
5. Start Session B with a new Button and the same short question (03), reusing this App's engine／child.
6. After KEEP_NEXT, deliver the multi-fragment question (05).
7. Deliver the same normal-close question; wait for cleanup; use supported graceful stop and bounded teardown.

Each mode has eight measured voice turns and four excluded close turns; 01 is measured on both launches.
No App survives into the next block, and PN may not warm the engine used for PH. Fresh App does not imply
OS reboot or filesystem coldness. Do not add pre-test inference; record existing startup prework and actual
IDLE→first-request interval. Begin each input only when real Listen readiness admits it, without a guessed
completion delay. USER presses Buttons, speaks the PH script and reports hearing; the observer maps cases
and records times automatically. Each PH measured-turn row includes USER hearing confirmation and
sanitized codes for unclear speech, stutter, perceived waiting and playback agreement with timing. Report
status is `CONFIRMED`, `FAIL` or `PENDING`; no hearing report is synthesized from Audio writes.
Do not silently relabel an early-ending or wrong-route turn as another case.

All fixed stimuli pass real ASR and current 20-codepoint／32-token admission. Fix the private fixture
binding and declared intent before execution; preserve decoded punctuation. A core-intent loss, R1 input-limit
response, fallback or missing real generation is not native-generation timing evidence. Record the route and
actual direct-user／rendered／context counts, keeping the failed／invalid sample. No transcript injection,
forced model route, rewritten question or post-result fixture substitution is permitted.

### 4.6 Real-time PN delivery and observation precision

PN uses 16 kHz mono signed 16-bit PCM, bound once, with 320-sample (20 ms) frames as in the existing runner.
For frame k schedule `t0 + k × 20 ms` on the Pi monotonic clock; record actual delivery and signed lateness.
The last padded frame and fixed trailing silence remain part of that binding. Do not burst-deliver overdue
frames to catch up. Speech end is the fixture's last speech-frame boundary on this schedule, separately
identified from ASR endpoint and final; it is not human speech end.

Predeclared pacing validity: retain nanosecond timestamps, report clock resolution, and record lateness with
at most 1 ms quantization. Every frame must be delivered no earlier than scheduled and no more than one frame
(20 ms) late; total delivery-span deviation must also be at most 20 ms. These are measurement-validity limits
for real-time input, not product response thresholds. A violation is `INVALID/PACING_DISTORTED`, not a slower
product PASS; retain the observation and stop the block. Do not enlarge limits after seeing results.

Collector timestamps are taken at the observed boundary, before text formatting or file flush. Report clock
resolution, timestamp quantization and a conservative boundary-hook／capture error bound before stimulus.
If an error bound cannot be supported, timings remain descriptive and cannot establish improvement. For a
duration use the sum of its two endpoint error bounds; for a before／after difference sum the two duration
bounds. Input-relative values additionally include actual pacing uncertainty. Do not infer timestamp error
from logger flush time, equate scheduling lateness with native duration, or claim all hooks have zero cost.
PH uses real microphone frames; speech end and acoustic onset are `unavailable/NOT_MEASURED` unless independently
measured. Missing those human-only measurements does not invalidate shared ASR-final／Audio-write comparisons.

### 4.7 Structured collector and diagnostic completeness

All required PN／PH observations use the same Pi-host monotonic clock and lossless structured timing-only
collector from the first request. Private correlation binds block／mode／case／Session／Turn, parent／child
request and fragment／TTS batch. Public rows identify cases and contain necessary timing, booleans, counts and
stable codes; process equality／reuse is a boolean, and raw request identities or content remain private.
Correlation loss, truncation, missing required nodes or mixed clocks is `INVALID/DIAGNOSTIC_INCOMPLETE`.

| Required boundary／fact | Semantics and admissible unavailable boundary |
| :--- | :--- |
| Input／ASR | Actual input mode, first frame, delivery interval; PN scheduled speech end; observable ASR endpoint and final. If no distinct endpoint exists, declare `NOT_EXPOSED` before execution and use last delivered frame→ASR final, without calling it endpoint latency |
| Conversation／parent／IPC | Conversation create／ready, resource READY, prior-generation boolean; parent GENERATE request send and child request receive, correlated to this Turn |
| Generation／safe text | Child native-generation start, first generated output, child first safe-text emit, parent first safe-text receive, child terminal and parent terminal receive |
| Native internal phases | Directly exposed render／prefill begin／end. If the runtime cannot expose a phase or first generated output, predeclare `NATIVE_NOT_EXPOSED` and the measurable enclosing boundaries; no synthetic timestamp or whole-interval prefill attribution |
| Speech pipeline | Fragment admission and queue-entry depth／wait, TTS batch start／first PCM, Audio first positive write and each segment complete／final drain, with fragment／batch mapping |
| Comparability | Direct-user input tokens, rendered input tokens, context tokens, and available output-token／output-size counts; actual GENERATE／fixed／fallback route, App／child／engine freshness／reuse, new Conversation, startup prework, IDLE→request interval |

Before the first block Developer records actually exposed native phases and exact count definitions in the
existing execution locator. Unexposed output tokens may use clearly labeled output-size counts; no estimated
tokens presented as measured counts. Parent／child boundaries and safe-text emit／receive are implementable
observer gaps to close, not optional native internals. A required observable boundary cannot be waived after
capture fails. Interpreting private ASR／model data is limited to intent or route diagnosis.

The legacy `llm_send_monotonic_ns` is child GENERATE native-start, not parent IPC send. Keep that retained
label／historical result intact; new evidence explicitly names parent send, child receive and native start.
Retain native-start→first-safe-text for comparison with old 12.762 s, and ASR-final→Audio-first-write for old
13.333 s. Audio write does not prove acoustic onset or complete audible playback.

For every reproduced slow sample retain its complete request and predetermined follow-up／new-Session samples.
Report which directly observed interval contains the wait, supported／excluded／unresolved hypotheses and the
minimum control needed to distinguish remaining causes. Only a 13 s send→safe-text number is insufficient.
An inaccessible native interior may remain unknown if matched observations support the analysis or bounded
experiment; do not invent warm-up／prefill causation or substitute content checks for timing.

### 4.8 Conditional `PN06`／`PH06` cause control

Enable 06 only when 02／03／04 cannot distinguish question differences, process-first, Session-first or context
influence. Record one concrete competing hypothesis and the compared endpoints before its first stimulus.
Each mode runs exactly two fresh-App blocks; each block has two Sessions with two measured turns each, all
four using `FX-SHORT-B`「一個星期有幾天？」, then one excluded normal close per Session. Use the same
Button／KEEP_NEXT／cleanup／shutdown steps and collector／pacing as above. Each mode adds eight measured
turns and four close turns. Retain the other mode's control even if only one mode exposed the discrepancy.

If used for before／after, execute this same structure on both sides. If first needed after a change, obtain
the missing before control on the retained baseline before claiming a comparison. Do not stop on the fastest
sample or add PN07／arbitrary repetitions. Remaining uncertainty produces a focused next action or an explicit
observation limit, not unlimited experiments or a fabricated cause.

### 4.9 Analysis, correspondence, failure and improvement decisions

Report each block／case's individual durations and two-block min–max range. Derive end-to-end intervals from
actual endpoints; overlapping LLM, TTS and Audio durations are separate and must not be summed. Identify the
largest measured interval and compare first／follow-up／new-Session patterns, token／output sizes and startup
costs. No averages, discarded slow samples, best-of or numerical latency acceptance threshold.

Pair PN／PH on native-start→safe-text, ASR-final→Audio-first-write and other equally observed boundaries.
Compare functional path, direction of first／warm differences and largest waiting interval. Compare exact
speech-end／acoustic values only if both modes measured equivalent boundaries. Explain differences using
observed input delivery, intent, counts or route facts; unmeasured context／warm-up is not an explanation.

- Product failure, early end, wrong required route or cleanup failure: `FAIL`; collector／pacing／correlation
  failure: `INVALID`. Stop the affected block, retain the first reason and all samples, mark unexecuted cases,
  and perform feasible bounded teardown. Do not automatically refill samples or retry for PASS.
- Human segment not executed／no hearing report: `PENDING`. A shared-time measurement cannot override hearing
  failure. A complete valid pair failing to reproduce the old slow symptom: `NOT_REPRODUCED`, never `fixed`.
- PN-fast／PH-slow without a verifiable explanation: discrepancy remains open; choose the smallest named
  control (06 only if its hypothesis applies) or fill a focused observation gap. ALPHA.P cannot complete while
  this discrepancy is unresolved. If both modes do not reproduce it, report scope／limits without forcing a fix.
- After an actual product／collector repair, use a new execution locator for affected observations; retain old
  failures and do not splice a stopped block into an apparently complete block.

Only one evidence-supported, localized, user-relevant improvement may be tried. Before editing product behavior,
record supported cause／limits, change location, predicted affected nodes, cost and functional risk. If cause
is not distinguishable, improve focused observation first. Low value or no supported opportunity permits a
no-change disposition. Neither warm-up, model replacement nor token-limit change is a preselected answer.

If tried, after repeats two PN and two PH fresh-App blocks using identical settings／questions／collector and
conditional 06 where enabled. Report all affected before／after intervals, startup and warm-path costs, and
retained failures. For each affected same-path case, both after samples must move in the claimed direction;
its before and after min–max ranges expanded by the measured endpoint error bounds must support that direction.
Overlapping ranges or insufficient counts are `INCONCLUSIVE`, not stable improvement. This is a conservative
claim about this experiment, not statistical significance or general stability. Moving waiting into startup,
precomputation, shorter output, fallback, early end or bypassing a real path is not an unqualified improvement.
If ineffective or regressing, retain results and reject the change; do not try a second optimization here.

### 4.10 `ALPHA.P` completion and regression

The existing development record must locate the timeout-capable entrypoint, fixed settings／fixtures, full
PN／PH blocks and enabled controls, precision／limits, correspondence, diagnosis and one disposition:
`NO_CHANGE`, `ADOPTED_ONE` or `REJECTED_ONE`. With no trial, no artificial after is required. Retained P's
`VALID_BASELINE` alone cannot close this round.

`ALPHA.P complete` requires complete valid paired observations (including an honestly scoped
`NOT_REPRODUCED` conclusion), finished PH hearing reports, no unexplained mode discrepancy, explicit
optimization disposition and passing directly affected portable／integration／hardware regressions.
Adopted changes also require directly affected L／R／Q coverage; targeted Q checks during development do not
replace final §6. Install the retained version at the existing fixed entrypoint, preserve the prior version,
and locate Pi verification of applicable same-content changes. Confirm workstation content matches the
Pi-verified content at the transfer boundary; no per-run automatic digest or startup check.

Final six-case Q is after ALPHA.P complete, so it is not a circular prerequisite for P completion. P completion
is not whole-ALPHA acceptance. Applicable final-version PN／PH results can be reused by Verify without another
pairing run; earlier product content is before／diagnostic evidence only.

## 5. `ALPHA-R01-LLM-RECOVERY`

### 5.1 Injection and steps

1. Start the production App to clean `IDLE`; record that exactly one production LLM child PID is READY.
2. Start a new Session using `FX-MULTI-FRAGMENT`.
3. Wait until at least one real `SAFE_TEXT` fragment is admitted into that turn's StreamingSpeak control. The
   runner then sends one termination request to that actual LLM child PID. This is the only injected fault.
4. Observe exactly one `LLM_BACKEND_FAILED` locator with `REBUILD_REQUIRED` and the LLM resource key.
5. Observe failure convergence and the recovery barrier. Attempt one Button admission during the barrier and
   require its rejection without creation of a Conversation or operation.
6. Wait for exactly one replacement LLM child to become READY.
7. Using a new Button trigger and new Conversation, execute one full normal Session: `FX-SHORT-A`, then
   `FX-NORMAL-END`, through real ASR → replacement LLM → legal TTS／Audio or direct-REST close.
8. After return to `IDLE`, request graceful shutdown and finalize owner checks.

### 5.2 Acceptance

The injected failing Session must show all of these:

- the killed PID is the sole pre-failure LLM child and the injection occurs after the required fragment admission;
- current generation stops, future fragment-admission count is zero, and queued／in-flight TTS and unplayed Audio
  converge to zero; content already played is not treated as reversible;
- no normal terminal `LLMResponse` or primary `ActionCompleted(status="ok")` is published for the failed turn;
- active Conversation, session-owned tasks, StreamingSpeak control, queues and in-flight operations reach zero;
- Display reaches `ERROR=錯誤` without retaining provisional answer content;
- the old child is terminated and reaped, Session admission is rejected during recovery, and exactly one
  replacement is created; no barrier crossing occurs before replacement READY.

The product-recovery proof must show all of these:

- replacement PID differs from the old PID and is the only READY LLM child;
- the post-recovery Session uses a new Button trigger and Conversation and completes real ASR → replacement LLM →
  TTS／Audio, then closes normally and returns to `IDLE`;
- no fragment, answer or context from the failed Session appears in the new Session;
- final graceful exit code is `0`; old and replacement LLM PIDs, all other product child PIDs, ALSA holders,
  Display fullscreen owner and all product hardware owners are absent.

Replacement startup alone is not a PASS. A missing assertion, second replacement, false injected terminal or
failure of the subsequent normal Session is `FAIL`.

## 6. `ALPHA-Q-RUN-01-QUALITY`

### 6.1 Execution and objective oracle

After ALPHA.P completes, start one clean final-version production App on the Pi. Run Q01–Q06 in the order below; after each single-turn case, close the Session with
the fixed normal-end fixture if it is still active and wait for cleanup. Q01–Q04 each use one Session; Q05 and Q06 each use
one two-turn Session. Close Q05 normally if still active; Q06 closes using its own T2.
Each case is executed exactly once. There is no retry, answer selection, prompt rewrite or replacement question.

For every case the runner records these objective results:

- fixture entered real ASR → LLM → TTS → Audio and all required terminals completed;
- terminal schema and action route are legal, response is non-empty where speech is required, and the expected
  keep／end behavior occurred;
- no schema, control marker or protocol fragment leaked into delivered speech;
- case and Session cleanup completed without late third turn or late output.

Any objective failure makes that case `FAIL` without semantic override.

### 6.2 Fixed cases and semantic oracle

Codex privately inspects the one candidate output and assigns the semantic disposition below. The sanitized public
reason must describe the criterion, not reproduce the response.

| Case / exact private stimulus | Required semantic result |
| :--- | :--- |
| `ALPHA-Q01-IDENTITY` / `FX-Q01` — 「請介紹你自己。」 | Identifies as a voice assistant or 雪板 in understandable natural speech; no exact wording. FAIL for impersonating a human／another brand or inventing a role／capability |
| `ALPHA-Q02-FACTUAL` / `FX-Q02` — 「一天通常有幾個小時？」 | Core answer is 24 hours, including spoken Chinese numbers and reasonable brief additions. FAIL for wrong number, evasion or material contradiction; no general-knowledge claim |
| `ALPHA-Q03-CAPABILITY` / `FX-Q03` — 「你能看見房間裡的東西嗎？」 | Expresses inability to see, or current hearing／speech only. FAIL for invented room view or claimed camera／tool availability; no fixed denial string |
| `ALPHA-Q04-INSTRUCTION` / `FX-Q04` — 「請用一句短話描述下雪的景色。」 | One short, continuously speakable snow-related description; politeness／natural pauses allowed. FAIL for unrelated topic, multi-part list, obvious verbosity or unintelligibility; no punctuation／mechanical word-count oracle |
| `ALPHA-Q05-CONTEXT` / `FX-Q05-T1`, `FX-Q05-T2` — T1「我喜歡滑雪。」; T2「我剛才說喜歡什麼？」 | T1 relevant and KEEP_NEXT; same Conversation T2 remembers liking skiing, synonyms allowed. FAIL for early end, forgotten／wrong preference, another Session's content or a new Conversation |
| `ALPHA-Q06-END` / `FX-Q06-T1`, `FX-Q06-T2` — T1「請聊聊冬天。」; T2「對話到這裡，請結束。」 | T1 relevant, brief and KEEP_NEXT; T2 END_SESSION with cleanup, brief farewell or legal textless REST allowed. FAIL for early end, continued conversation, late third Turn／audio or incomplete cleanup |

Fix `Q-20261011` fixture revision and current admission eligibility before viewing results. Real ASR word
variation is allowed when intent survives; loss of core intent is not excused by attribution to ASR. Preserve
punctuation and the current input envelope; do not alter transcript／route to admit a fixture. Previous Q stimuli
are retired. `ALPHA-Q-DEV-20261003-02` remains objective 6／6, semantic 4／6 with original Q05
`LOCATION_FACTUAL_ERROR` and Q06 `ARITHMETIC_INTENT_LOST_IN_ASR` FAIL. These are result locators, not inputs to
rerun or outcomes to overwrite. USER's prior overall quality acceptance does not waive this final regression.

Identity, stated fact, capability honesty, relevance, explicit instruction following and multi-turn coherence are
contractual and therefore receive `PASS` or `FAIL`. `NEEDS_USER_DECISION` is allowed only when private evidence is
insufficient, a reasonable factual dispute remains, or a product preference is not fixed by the rubric. It must
name the single unresolved issue in sanitized form and routes only that issue to USER; it is not a second judging
round. ALPHA cannot be Accepted while any case remains `NEEDS_USER_DECISION`.

### 6.3 Quality run verdict

The quality run is `PASS` only when all six cases have objective `PASS`, semantic `PASS`, no retry, and completed
Session cleanup. One objective or semantic `FAIL` makes the run `FAIL`. Otherwise any permitted unresolved case
makes the run `NEEDS_USER_DECISION`. Public evidence contains one row per case with objective booleans, semantic
disposition and sanitized reason; raw answers, transcripts and audio are excluded.

## 6A. `M` — final-version free conversation and operation

### 6A.1 Value, retained background and entry

M answers what fixed PCM cannot: real microphone input, audible usable output, Display and natural operation.
It is independent of PH's fixed timing script. Existing live experiments, failed launches／operations, repaired
retest and incidental timings remain classified and located by ALPHA §6A and its existing development.md
sections. Do not manufacture historical M cards／run IDs, infer missing exit status, rewrite failures or claim
old live intervals are PN／PH evidence. `19d9ca2` repair remains delivered; old first-response causes are unproven.

Before execution fix in the existing evidence／owner record the run locator, retained final content／installed
entry, launch-to-stop scope, and separate PH／M segment labels if sharing one human session. No extra Markdown,
identity sign-off or historical source reread is required to create this specification.

### 6A.2 Steps and acceptance

1. Launch the final retained version through the formal fixed installed entry; wait for READY／IDLE and clean Display.
2. USER starts Session A and freely chooses at least two substantive interactive Turns within the current
   short-input envelope. Use real Button／microphone／speaker／Display; questions are not fixed Q or PH fixtures.
3. Through supported operation return to standby and complete Session cleanup.
4. USER starts a new Session B and completes at least one substantive interactive Turn, proving reuse.
5. Through supported operation return to standby and stop App. Operator retains actual stop status and directly
   relevant App／product-child／hardware-release observations, with a finite operation／teardown watchdog.
6. Obtain USER's report on actual input recognition, hearing／usability, Display agreement, continued conversation,
   reuse and normal operation. State transitions alone cannot decide human experience.

Public evidence contains segment locator, required-turn counts, input／audible-output／Display-agreement／reuse／
standby／stop booleans, observed exit-success and relevant owner-release booleans, USER report status and
sanitized failure code／reason. No raw spoken text／PCM. `PASS` requires all functional observations, actual
successful supported stop (exit code `0`)／release, and USER confirmation of usable hearing／operation. Missing USER report
is `PENDING`; observed interruption／end／restart／stop failure is `FAIL`, even if the product later recovers
IDLE. Natural pauses／corrections may be noted; no forced fault, noise scenario, stopwatch gate or interruption
matrix. Accepted knowledge limits do not waive Q.

The shared observer may retain timing during M. A renewed first-response delay preserves analyzable request
boundaries and returns to P diagnosis; free questions are not controlled PN／PH before／after samples. PH and
M may share an actual user session only with distinct segments／results. Earlier-version M is background only;
applicable final-content M results can be reused without duplicate free-use testing.

## 7. Required runner interface and evidence

Use one timeout-capable ALPHA entrypoint selecting Lifecycle, retained Performance P, automatic PN, guided
human PH, Recovery or Quality. CLI names／deployment parameters are Developer-owned and must be recorded
in existing `docs/status/development.md`; the contract fixes behavior, not invented implemented flags.
Current L／P／R／Q selector examples remain:

```text
python scripts/run-alpha-pv.py --run lifecycle   <deployment arguments>
python scripts/run-alpha-pv.py --run performance <deployment arguments>
python scripts/run-alpha-pv.py --run recovery    <deployment arguments>
python scripts/run-alpha-pv.py --run quality     <deployment arguments>
```

PN and PH selectors must run／guide the declared block schedule, record mode／before-or-after／block and fixture
revision, and support explicit conditional 06 activation with its named reason. PN is fully automatic from
startup through close／shutdown; PH guides physical operations and automatically captures the same collector.
Retained P behavior remains separately selectable. M uses the installed real-input entry and applicable
shared observation, with a separately identified free-use result; no need for a duplicate M automation harness.

The existing 900 s runner watchdog and 20 s bounded cleanup default may be used for each automatic block;
PH／M use a predeclared finite 1800 s operation window and 20 s teardown allowance for human pacing. Overrides
must be recorded before stimuli. None is a product latency threshold; actual product completion controls
steps. Timeout stops the affected block／segment with retained reason and unexecuted rows. No silent retry.

Return non-zero for `FAIL`, `INVALID`, unresolved `NEEDS_USER_DECISION`, `PENDING` or an open discrepancy;
retain the first failure and still perform bounded cleanup. A complete valid `NOT_REPRODUCED` result can finish
successfully with its limitations, but may not be relabeled fixed. Public output contains:

- Run／segment locator, disposition, necessary target facts, fixture／question revision and IDs.
- Only the run's required booleans, counts, stable codes, monotonic boundaries and sanitized reasons.
- Failed／invalid samples and unexecuted cases; no hidden sample substitution.
- Required process／hardware final-release observations for L／R／M and shutdown results for P／Q;
  do not append a generic owner enumeration to every case.

Retained P evidence has its original P01–P05 nodes. PN／PH evidence has all applicable §§4.5–4.9 observations,
individual durations／ranges／error bounds, native limits, correspondence and improvement disposition. Q has
six objective and semantic rows with fixture revision. M has §6A observations and USER report. Only L performs
the aggregate network／privacy scan. Reject forbidden public content before emitting a passing disposition;
no digest is computed by a test／collector／startup as evidence integrity or as a PASS assertion.

## 8. Coverage and Developer entry

| ALPHA authority | Direct executable coverage |
| :--- | :--- |
| Opening five-area table; §3 repeated use, shutdown／restart, offline／privacy | §1 and §3; updated `FX-SHORT-A` in §2.2 |
| §4.2 retained P01–P05 and fixtures／results | §§2.2, 4.1–4.4; no automatic historical rerun |
| §4.5 PN01–PN05／PH01–PH05, shared observation and slow-sample diagnosis | §§4.5–4.7; mode／case bindings and exact order |
| §4.7 two fresh-App blocks per mode, pacing／uncertainty, conditional 06 | §§4.5–4.9; fixed validity bounds and control schedule |
| §§4.6–4.7 paired comparison, at most one improvement, P completion／reuse | §§4.9–4.10 and §7 |
| §5 real child fault, convergence, one replacement, next normal Session | §5 with current `FX-MULTI-FRAGMENT` binding |
| §6 revised six questions／minimum usability and retained FAIL | §6 with `Q-20261011`, once after P, objective and Codex semantic oracles |
| §6A M free use, human report／stop, retained background and separate PH segment | §6A; final installed content, two Sessions, no fabricated history |
| §§7–8 Developer／Verify entry, five-area final-content conclusion | §§7–8; implementation gaps and evidence reuse without extra gate |

### 8.1 Test Spec disposition and next owner

Tester synchronization disposition (2026-10-11): **READY_FOR_DEVELOPER**. All current ALPHA §7 requirements
are mapped above to Test IDs／case bindings, fixed steps and verdicts. This is specification readiness, not a
product execution PASS. Workstation document checks passed: local links, heading／fence structure, all eight
revised Q stimuli against design, retired-stimulus removal and `git diff --check`.
The current task is Test Spec preparation; candidate designation is required before
actual Verify, not a new prerequisite for this design-authorized synchronization.

Next owner: **Developer**. Estimate actual shared collector／parent-child correlation／PN pacing／PH guide and
revised-fixture gaps, preserve the installed repair and retained P mode, execute the paired baseline, diagnose
and try at most one supported improvement. Record exact executable commands／native limits in existing
`development.md`. No additional role approval, review round, freeze or handoff file blocks implementation.
Designer owns any later update of `status/current.md`; Tester does not edit it.

Delivery disposition (2026-10-18): **COMPLETE FOR DELIVERY by USER decision** for retained delivery
`8b4af53f433c4bcdb5b858973e10767318986554`. Existing same-content Pi evidence includes affected regression,
Lifecycle, Recovery and revised-Q results; USER also completed final-version real microphone operation,
cross-Session reuse, normal return to standby and normal stop. The historical PH script interruptions and the
absence of a separately labeled M card are retained as limitations, not a reason to demand repeated human
tests after USER accepts the delivered behavior. The punctuation-only TTS fragment and isolated audio capture
finding are deferred follow-up observations. No Pi or human test was executed by this documentation update,
and no earlier candidate is spliced in.

### 8.2 Final Verify and ALPHA exit

On one final retained product content, finish L／R PASS, six revised Q objective／semantic PASS after ALPHA.P,
valid complete PN／PH with closed correspondence and explicit optimization disposition, and M PASS including
USER confirmation and successful supported stop／release. All applicable automatic, integration, hardware and
human checks run on the Pi against the same pending content; workstation content must match Pi verification.
Final-content applicable PN／PH／M or affected functional evidence may be reused without duplicate execution.
Never splice earlier candidates, rewrite old FAIL or rerun Accepted matrices solely for closure.

ALPHA.P complete is distinct from whole-ALPHA Accepted; no unresolved Q decision, P discrepancy, actual failure
or M human report remains at exit. Accepted product limitations stay explicit. This specification does not
authorize commit／push; any later Git delivery follows the existing Git rules.
