# ALPHA Test Spec — Voice-only product convergence

## 1. Authority and purpose

This specification maps [`../milestones/ALPHA.md`](../milestones/ALPHA.md) into four executable Raspberry Pi
runs. It does not reopen M4／M4C qualification and does not add product capability.

| Test ID | Product risk answered | Required disposition |
| :--- | :--- | :--- |
| `ALPHA-L01-LIFECYCLE` | Repeated use, cleanup, shutdown or restart leaves stale work or owners | `PASS`／`FAIL` |
| `ALPHA-P01-PERFORMANCE` | User-visible delay cannot be attributed to a concrete path stage | `VALID_BASELINE`／`INVALID` |
| `ALPHA-R01-LLM-RECOVERY` | A real LLM child failure leaks old output or cannot return the product to service | `PASS`／`FAIL` |
| `ALPHA-Q-RUN-01-QUALITY` | The complete voice path produces unusable or misleading answers | `PASS`／`FAIL`／`NEEDS_USER_DECISION` |

The four rows are independent runs. The six quality cases are six fixed cases inside one quality run, not six
additional fresh-start runs. Offline and privacy are assertions embedded in Lifecycle, not separate Test IDs.

### 1.1 Value and risk pruning

Each retained assertion observes a user-visible product failure: stale cross-session state, incomplete owner cleanup,
unexplained path delay, failed recovery, or unusable speech output. The following add no ALPHA decision value and
must not be collected as acceptance work:

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
Performance, Recovery and Quality must each begin with no product App process left from a previous run. A runner
precondition failure makes that run `INVALID`; it must be corrected before the single valid execution begins.

Every command has a finite runner watchdog recorded before execution. The watchdog only prevents an unbounded
harness hang; it is not a response-time requirement and its duration is not reported as a product threshold. Once
the first product stimulus is admitted, timeout, runner crash, fixture substitution or lost required observation
ends the run as `FAIL`／`INVALID` as specified below; the runner may not retry the case to obtain a better result.

### 2.2 Fixed fixtures

Before execution, the runner resolves these local PCM identities. Exact paths may be deployment-specific, but the
mapping and audio bytes stay unchanged within the candidate's four runs. Public evidence records only the fixture
ID, never transcript or PCM content.

| Fixture ID | Private spoken content / use |
| :--- | :--- |
| `FX-SHORT-A` | Eligible short request: 「一加一等於多少？」 |
| `FX-SHORT-B` | Eligible matched short request: 「一個星期有幾天？」; used by both P02 and P03 |
| `FX-FOLLOW-UP` | Session A follow-up: 「請再簡短回答一次。」 |
| `FX-MULTI-FRAGMENT` | 「用三句短話介紹滑雪注意事項。」 |
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

### 4.4 Optional bounded improvement

An implementation change is allowed only after the valid baseline identifies one clear, localized and
user-relevant bottleneck. At most one improvement work item is opened. It reruns P01–P05 with the same fixtures and
measurement settings and reports every directly affected node as before／after; all observations remain visible.
No improvement may be claimed unless the change is stable beyond the recorded measurement uncertainty. An adopted
change also reruns only directly affected Lifecycle, Recovery, Quality and portable regression coverage. If the
baseline exposes no clear bottleneck, this subsection creates no development work.

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

Start one clean production App. Run Q01–Q06 in the order below; after each single-turn case, close the Session with
the fixed normal-end fixture if it is still active and wait for cleanup. Q05 and Q06 are each one two-turn Session.
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
| `ALPHA-Q01-IDENTITY` / `FX-Q01` — 「請問你是誰？」 | Identifies as the local snowboard／voice assistant; does not impersonate a human, another branded assistant or an undefined role; concise enough to speak |
| `ALPHA-Q02-FACTUAL` / `FX-Q02` — 「一個星期有幾天？」 | Says seven days; any addition is brief and not wrong, evasive or contradictory |
| `ALPHA-Q03-CAPABILITY` / `FX-Q03` — 「你現在可以看到我前面的東西嗎？」 | Explicitly acknowledges no current vision ability; invents no camera scene, environment or unavailable tool |
| `ALPHA-Q04-INSTRUCTION` / `FX-Q04` — 「用一句話說初學滑雪為何要戴安全帽。」 | One sentence, directly relates helmet use to beginner skiing, concise, with no plainly dangerous or incorrect guidance |
| `ALPHA-Q05-CONTEXT` / `FX-Q05-T1`, `FX-Q05-T2` — Turn 1「請簡短介紹台灣。」; Turn 2「再簡單一點，並且只說它的位置。」 | Same Conversation; Turn 2 resolves 「它」 to Taiwan, is simpler, and contains only location-focused content |
| `ALPHA-Q06-END` / `FX-Q06-T1`, `FX-Q06-T2` — Turn 1「請不要結束對話，先告訴我一加一等於多少。」; Turn 2「現在請結束對話。」 | Turn 1 says 2 and keeps the Session; Turn 2 ends it without reversal, new topic or late third turn |

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

## 7. Required runner interface and evidence

Developer may choose internal implementation, but the delivered ALPHA runner must expose one timeout-capable
entrypoint that can select exactly one run, for example:

```text
python scripts/run-alpha-pv.py --run lifecycle   <deployment arguments>
python scripts/run-alpha-pv.py --run performance <deployment arguments>
python scripts/run-alpha-pv.py --run recovery    <deployment arguments>
python scripts/run-alpha-pv.py --run quality     <deployment arguments>
```

The runner must return non-zero for `FAIL`, `INVALID` or unresolved `NEEDS_USER_DECISION`, preserve the first
failure and still perform bounded final cleanup. Public output for each invocation contains:

- run ID, disposition, target facts and fixture IDs;
- the exact booleans, counts, stable codes and monotonic nodes required by that run;
- a sanitized failure／invalid／decision reason when disposition is not passing;
- final cleanup booleans for App process, product children and hardware owners.

Performance evidence additionally contains all P01–P05 nodes and derived durations. Quality evidence additionally
contains the six objective and semantic rows. Lifecycle alone contains the aggregate network and privacy counts.
The evidence producer must reject forbidden public fields before it can emit a passing disposition.

## 8. Coverage and Developer entry

| ALPHA authority | Direct coverage |
| :--- | :--- |
| Lifecycle startup, 3 Sessions × 2 Turns, cleanup, shutdown, owner absence, restart, offline, privacy | §3 |
| Separate P01–P05 characterization, validity and bounded before／after rule | §4 |
| Real LLM child termination, convergence, one replacement, new normal Session, final owner absence | §5 |
| Six fixed cases once, objective path oracle, Codex semantic oracle and USER-only unresolved route | §6 |

Developer entry opens when implementation work is limited to actual gaps needed to execute §§3–7. Development
estimates must not add excluded ALPHA work. Final Verify runs all applicable automatic, integration, hardware and
human observations on the Raspberry Pi against the same candidate content. Lifecycle, Recovery and all six
Quality cases must pass; Performance must produce a valid complete baseline. Results from different candidates
may not be combined into one ALPHA conclusion.
