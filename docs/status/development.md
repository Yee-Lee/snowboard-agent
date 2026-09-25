# Current development status

## Active M4C implementation — 2026-09-25

### Authority and execution model

- Developer entry is Open by `docs/status/current.md`. Product authority is
  `docs/milestones/M4C.md`; executable authority is `docs/test_spec/test_spec_M4C.md`, with later
  explicit USER decisions taking precedence where those owner documents are still stale.
- M4C uses two lanes. Discussion closes one scenario's stimuli, evidence, assertions and workstation
  try-run. Implementation then completes that scenario through workstation try-run and applicable Pi
  product testing. After every scenario converges, the final pending bytes receive one complete Pi PV
  before the M4C completion commit.
- Assertions must detect a stated product risk. Scenario startup and execution do not perform routine
  source, model, artifact, evidence or text digest work, generic close-proof, or owner enumeration.
  Content checks remain operator-triggered transfer/candidate diagnostics only when actually needed.
- Pi scenarios use the selected INMP441/ALSA input and I2S speaker. No M4C result depends on
  external capture or exact ASR wording.

### Current implementation result

- WP1–WP5 are implemented across fixed output volume, B2 streaming extraction/control, authenticated
  `SAFE_TEXT` delivery, streaming Speak and Display integration, no-input session policy, and the M4C
  scenario runner. S02 is recorded by commit `900a91f`; the completed S03 delta remains in the working
  tree pending the next milestone commit decision.
- Workstation verification is green: the complete non-RPi suite, focused M4C/M4B regressions,
  compilation and diff checks pass. Pi verification is green for the complete non-RPi suite and the
  focused startup/worker/runner/S02 matrices. A display-null cold start reached Resource Manager READY
  in 3.555 seconds with zero cleanup failures; ASR took 0.371 s, Matcha TTS 2.567 s and LiteRT-LM
  0.525 s. The OLED was not opened.
- Product startup/rebuild now uses bounded path-shape checks instead of repeatedly hashing the 2.58 GB
  model and runtime closure. Full digest helpers remain available only for explicit staging or
  candidate diagnostics. This removed the observed 60–90 second startup delay without changing native
  READY identity or offline/network-denial behavior.
- LiteRT-LM streaming now waits for asynchronous 0.16 callbacks after the native entry returns, and
  partial JSON immediately after `{"text":` is treated as incomplete rather than invalid. Timing
  validation checks generation and playback causal branches independently, allowing the required
  `audio_first_write < llm_terminal` overlap.

### S02 — implementation closed

- `M4C-PI-S02/NORMAL_END_B2` incorporates the former live-eligible S09 proof. Turn 1 requires
  `first_safe_text <= tts_first_pcm <= audio_first_write < llm_terminal`, complete ordered playback and
  drain, and equality between synthesized, terminal and final Display text. Turn 2 accepts the legal
  `speak, speak, rest` or `speak, rest` action branch and returns to IDLE. ASR text itself is not graded.
- Pi run `M4C-S02-DEV-20260924-09/A1` completed both physical-button/INMP441 turns, two streamed speaker
  answers, post-answer Rest, clean shutdown and return to IDLE. All product assertions preceding Display
  adjudication passed. Its immutable result card remains Fail only because the driver omitted the valid
  `("WAKE", null)` Main-clear publication from a duplicated expected ledger; this is a harness false
  negative, not a product failure.
- The Display expectation now comes from one oracle for both legal second-turn branches. The corrected
  workstation and Pi focused matrices pass, including checkpoint-before-adjudication coverage. Per USER
  direction, no duplicate physical interaction is required; the corrected harness runs again as part of
  final full M4C Pi PV. The initialized RUN10 was not executed and carries no result.

### S03 — implementation closed

- `M4C-PI-S03/TWO_TIMEOUTS` uses one short press to create a Session/Conversation. Two real 10-second
  INMP441 captures while the operator remains silent each classify as `timeout`. The first plays exactly
  one fixed retry prompt to completion before the second capture. The second calls no LLM, plays no retry,
  executes Rest/END_SESSION and returns to IDLE with Status `待命` and empty Main.
- The workstation try-run is implemented with the real State Manager, Speak, Rest and SessionDisplay over
  fake native endpoints. It proves two `timeout` results in one Session, streak `1 → 2`, one fully completed
  retry playback before the second Listen starts, exact fixed retry selection, zero Reasoner calls, Rest and
  final IDLE/Main-empty behavior. A shared oracle rejects wrong classifications, a second retry, changed
  Session, early second Listen, any LLM call and incomplete playback. Raw observations are checkpointed
  before adjudication so a harness-only defect does not force another physical run.
- The focused workstation and same-byte Pi matrices pass **48/48**; Python compilation and
  `git diff --check` pass. Pi run
  `M4C-S03-DEV-20260925-01/M4C-S03-TWO-TIMEOUTS-20260925T122119Z-1785` passed the physical button,
  two real silent INMP441 windows, one complete speaker retry, zero Reasoner calls, one Rest and final
  IDLE cleanup in 80.75 seconds. The OLED remained unopened through a `null` display driver.
- The public result contains only stable counts, booleans and state codes. Exact ASR text is not asserted,
  and the runner performs no per-sub-run source/config/model/artifact/evidence digest validation.

### S04 — implementation closed

- S04 is the sole Pi product-level short-press interrupt scenario. It uses three fresh sub-runs, exactly
  once each: active PERCEPTION capture, active THINK generation and ACTION with audio playback active.
  These are three distinct cancellation paths, not repeated reliability rounds.
- Each variant must prove that the physical short press is accepted as interrupt, Main publishes
  `已中止` and is cleared at final IDLE, the affected operation stops, no old-operation normal success or
  late effect is accepted, and only the directly affected lifecycle is clean before returning to IDLE.
  It does not add SHA/digest, startup/config checks, generic close proof, global owner enumeration,
  latency grading, a second Session or human adjudication.
- The product now projects Main=`已中止` only when an active Session accepts a short-press or interrupt;
  final IDLE still clears Main. The workstation try-run uses the real State Manager, SessionDisplay and
  Speak cancellation path with named fake-native barriers at active capture, active generation and active
  playback. Its shared oracle rejects an inactive interrupt, missing Display projection, old-operation
  success, a post-interrupt restart, fabricated system fault or incomplete affected-owner cleanup.
- The focused workstation and same-byte Pi matrices pass **61/61**, including all three S04 paths plus
  S02/S03, runner and checkpoint compatibility. The Pi driver is implemented with live barriers inside
  actual ASR capture, LiteRT-LM `generate()` and the first speaker hardware write; the operator is prompted
  only after the selected operation is active. If ASR needs the product's second Listen window, the script
  prompts again;
  returning to IDLE before the target barrier now fails immediately instead of waiting for the scenario
  timeout. Raw observations are checkpointed before oracle adjudication.
- S09 is not a second Pi interrupt matrix. Normal streaming is covered by the completed S02 product run;
  queued/synthesizing controller races remain low-cost workstation coverage; S04/ACTION subsumes the
  former S09/PLAYING product run by interrupting actual hardware playback. Because B2 intentionally starts
  Speak during THINK, the recorded State may be THINK or ACTION; the active playback operation, not an
  impossible state/playback conjunction, defines this variant. No later S09 Pi interrupt sub-runs are to
  be implemented.
- Pi runs `M4C-S04-PERCEPTION-20260925T132416Z-4300` and
  `M4C-S04-THINK-20260925T133053Z-10276` passed their physical short-press barriers. ACTION run
  `M4C-S04-ACTION-20260925T133651Z-12986` interrupted actual speaker hardware playback while B2 was in
  THINK, showed `已中止`, published no old response/action success or late playback, left the affected
  owner idle and returned to IDLE with Main empty. Level-1 Reasoner cancellation escalated through the
  normal Level-2 recovery path without an `ErrorOccurred` event.
- The immutable ACTION card is Fail only because the previous oracle required a generic
  `session_interrupt` close call that Level-2 recovery does not use. The raw checkpoint passes the corrected
  oracle on Pi, and the same-byte focused matrix passes **61/61**; no duplicate physical ACTION run is
  required. Next action is the S05 work package. Final full M4C PV remains pending until all scenarios are
  complete.

### S05 — implementation and Pi verification complete

- Scope remains one `M4C-PI-S05/APP_EXIT` sub-run from application READY / State Manager IDLE. It retains
  only the direct shutdown risks: one long-press shutdown signal, no WAKE/new Session, application exit `0`,
  shutdown Blank before Display close, zero aggregate resource-stop failures and zero surviving native
  child processes. The watchdog is hang protection, not a latency grade; OLED human judgment, active-state
  variants, exact owner order/enumeration, restart/soak and SHA/digest checks remain excluded.
- Affected paths are `scripts/m4c_s05_oracle.py`, `scripts/m4c_s05_app.py`,
  `tests/test_m4c_s05_tryrun.py`, `tests/test_m4c_pv_rpi.py`, `tests/test_m4c_reg_001.py` and this active
  snapshot. The implementation is harness/oracle only; no product behavior source is changed.
- Workstation command `PYTHONPATH=src python3 -m pytest -q tests/test_m4c_s05_tryrun.py
  tests/test_m4c_reg_001.py tests/test_m4c_pv_runner.py` passes **26/26** with no Skip. The try-run executes
  the real top-level `run_app()` / State Manager / Resource Manager / M3 Display shutdown path using the
  default fake backends and a simulated legal shutdown signal.
- The Pi driver launches the exact-product application as a child process. A surviving outer pytest process
  waits for an application-owned READY marker, prompts the physical long press, records application exit and
  the direct process-tree cleanup result, then adjudicates the checkpointed raw observation. The same-byte Pi
  focused matrix passes **26/26**, including deliberate inherited coordinator variables.
- Physical run `M4C-S05-APP-EXIT-20260925T141859Z-14406` passed
  `M4C-PI-S05/APP_EXIT`: application exit `0`, no Session accepted, shutdown Blank before Display close,
  zero aggregate stop failures and zero surviving native child processes. S05 is complete; no additional
  long-press variants or rerun are required. Next action is the next M4C scenario work package.

### S06 — discussion closed; workstation-only gap closure after S05

- Do not implement the three proposed Pi sub-runs `PERCEPTION_ASR_INFERENCE`, `THINK_LLM_CHILD_EXIT` and
  `ACTION_TTS_CHILD_EXIT`. The accepted M4-ERR chain already proves ASR/LLM/TTS fault mapping, safe
  Display/log projection, transition through ERROR to IDLE, real child destruction/rebuild and successful
  handling of the next request. In particular, the ASR case already proves that inference failure publishes
  no `PerceptionResult`, does not retry or call the Reasoner, and still converges to IDLE.
- Retain only two M4C-specific, low-cost workstation regressions: an LLM that emits a partial streaming
  fragment before its backend fault must clean the StreamingSpeak path without `LLMResponse` or successful
  `ActionCompleted`; and a TTS child fault received by StreamingSpeak must clear queued/audio work, publish
  exactly one `ErrorOccurred`, and never publish successful `ActionCompleted` for that operation.
- These regressions do not add a cause matrix, second Session, recovery-latency grade, global owner
  enumeration, SHA/digest or closure evidence. They extend current streaming integration coverage without
  reopening or rerunning the accepted M4-ERR stage. Designer and Tester must remove the superseded S06 Pi
  entries from their authority/catalog before final formal M4C PV; this does not block implementation.

### S07 — discussion closed; one workstation integration regression

- Remove the proposed `M4C-PI-S07/DISPLAY_DEGRADE` sub-run. Existing M3 Pi coverage already exercises the
  real OLED write/lifecycle path, while accepted M3/M4-ERR regressions prove that a Display exception is
  caught locally, latches rendering disabled, emits one `DISPLAY_RENDER_DISABLED` diagnostic and prevents
  later hardware writes. Reinjecting that deterministic software exception on Pi adds no hardware-risk
  coverage.
- Retain one low-cost workstation vertical regression for the only uncovered product risk. During a normal
  Session, inject one fake Display `show()` failure when the THINK projection writes the final ASR text;
  prove that rendering is disabled with one diagnostic and no later device call, no `ErrorOccurred` or
  ERROR state occurs, LLM → TTS → Audio still completes, and Session cleanup reaches IDLE.
- Do not add multiple failure points, repeated rounds, OLED human judgment, application startup/exit,
  generic lifecycle closure, global owner enumeration, SHA/digest or evidence packaging. S05 separately
  owns application exit, so S07 need only prove Display-failure isolation from the active voice path.
  Designer and Tester must remove the superseded S07 Pi entry from their authority/catalog before final
  formal M4C PV; this does not block implementation.

### Current authority route

- `docs/milestones/M4C.md`, `docs/test_spec/test_spec_M4C.md` and the active runner still list four S09 Pi
  variants and a 16-run catalog. This is superseded by the USER decision above; Designer and Tester must
  remove the redundant S09 Pi entries and publish the resulting catalog before final formal M4C PV.
- The Tester-owned Test Spec command examples and evidence wording still contain the superseded
  `--binding-manifest`, digest and normal-session close-proof boilerplate. The project-wide `AGENTS.md`
  rule takes precedence, so this does not block the S03 development Pi run; Tester must remove that stale
  wording before the final formal M4C PV. Developer does not reintroduce those checks in the runner.
