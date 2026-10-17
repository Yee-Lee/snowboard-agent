# Current development status

## Active ALPHA implementation

### Delivery closeout — 2026-10-18

- USER requests completion, commit/push and Pi shutdown. Current branch is `core`, HEAD `f9955af`;
  this delivery is still uncommitted. Follow AGENTS/git.md: finish Pi verification, reconcile bytes,
  scan staged privacy, present full commit message/files for the required confirmation, then push.
  No completion tag or whole-ALPHA Accepted claim is authorized by the current evidence.
- Formal `run.sh` and `run.sh --debug` now select `asr-notice-20261017-r11`; previous r9 is retained.
  Promotion compared 17 affected source/test files directly across workstation, Pi checkout and
  installation: no difference, `<r11-root>/promotion-byte-comparison.json`. No automatic digest was added.
- USER explicitly defers the isolated `audio` capture/cleanup issue until recurrence and reports improved
  capture after repositioning hardware. Do not resume gain/model/prompt tuning or use older-position
  recordings as current hardware-quality proof. Display content/layout is deferred; ALPHA preserves
  ERROR state, safe codes/categories and recovery for future Display projection. No extra human repeat
  is needed merely to change the root symlink to identical tested bytes.

#### Delivered implementation and bounded verification

- `WhisperCppASRAdapter`: native request faults keep the backend BUSY until termination; cancellation
  cannot abandon owned destruction. Listen settles its owned transcribe reader before closing capture,
  including a deadline before the first frame. The regressions reproduced failures before each repair.
- `StateManager`: non-LLM recovery closes the surviving LLM Conversation before the next Session.
  ASR system faults retain their original error/recovery path, then use supervised Speak/TTS/Audio to
  announce 「語音辨識發生錯誤，請按按鈕重新開始。」 once before IDLE. Only the correlated notice fact is
  accepted in ERROR; new admission waits for playback completion. Shutdown can stop the notice, and a
  secondary speech fault converges without replaying it. Ordinary no-input keeps its existing retry
  prompt and re-capture; wrong recognized text is not automatically detectable as a system fault.
- `StatusBar` clears the stale error slot on ERROR-to-IDLE. `CognitionObserver.finish()` clears speech
  marks when no Reasoner turn began, preventing no-input speech from contaminating a later Turn.
- Standard launcher `--debug` packages reusable private physical-input recording, exact bounded native
  WAV retention, private native/fatal causes, display presentation observations and independent bounded
  post-error panel clear. Original FAIL/exit facts are preserved. Ordinary startup has no post-fatal
  clear; Ch 11 fatal policy is unchanged. Saved-WAV replay and custom acoustic tests are diagnostic,
  never fixture/quality PASS substitutes. Workflow: existing runbook §9, no new handoff Markdown.
- Product Whisper remains **base-q8_0**, four threads, fixed technical prompt/decoder; VAD, capture gain,
  model and timeouts are unchanged. Replay gain changes a private copy only; no original recording edits.
- Workstation and Pi combined affected regression: **311 Pass** each (24.93 s / 6.48 s). Pi result:
  `<operator-home>/alpha-delivery-20261018-r11/affected-portable.log`. Selection includes manual debug,
  alpha product/runner, launcher/install, ASR, LLM observation/generation, no-input, State Manager,
  display recovery, M4-ERR and interrupt regressions. Earlier r11 selections were 151 + 82 Pass.
- Native lifecycle and actual LLM recovery both PASS at
  `<operator-home>/alpha-delivery-20261018-r11/{lifecycle,recovery}/result.json`: three clean Sessions,
  restart/offline/privacy checks, actual child failure and one usable replacement, final owner release.
  Revised Q regression with retained `Q-20261011` fixtures was interrupted by a host reboot around
  00:26:45 +08 on 2026-10-18; SSH ended 255 and no quality result or semantic report was saved.
  USER reports no manual reboot or power cut. No automatic retry or parallel Pi work was performed.
  USER subsequently explicitly requested completing Q: the fresh full run
  `ALPHA-QUALITY-DEV-20261018-R11-02` completed all six cases once, objective 6/6 and semantic 6/6,
  six clean Session barriers and all final owners absent. Evidence:
  `<operator-home>/alpha-delivery-20261018-r11/quality-02/adjudicated-result.json`; initial pending
  card and private observations/judgments are preserved, with no product replay during adjudication.
  Existing PN/PH hearing gaps remain explicit; these runs cannot
  manufacture ALPHA.P completion or formal Q admission after an unproven P completion.

| Same-content evidence | Observed result / locator |
| :--- | :--- |
| ASR fault notice and usable replacement | Actual ASR child termination, replacement READY, exact notice once, completed playback, no auto-capture before Button, next live-microphone acoustic question fully answered, exit 0; `<r11-root>/installed-native-notice-02/`, independent post-exit PID/owner/black-display check |
| Installed normal entry | `<r11-root>/installed-entry-acoustic-02/`: VALID_OBSERVATION, expected question, full response, exit 0, zero errors, all cleanup true. External exception-only capture hook; no product bytes changed |
| Fixed root entry | `debug-fixed-entry-smoke-7ag85ymp`, manual `manual-26mvrheg`: zero Sessions, IDLE/SIGINT, exit 0, normal final black display and no owners |
| USER manual normal stop | `manual-9510k6gj`: 3 Sessions / 10 capture records, exit 0, zero errors, all cleanup true |
| USER fixed-entry retest | `manual-zvfo51jx`: 3 Sessions / 9 capture records, exit 0, zero errors, all cleanup true; USER reports completion |

Capture counts are not counts of successful answers. The two completed human runs have no WARNING,
ERROR or CRITICAL. They provide real operation/stop evidence, not injected-fault proof or fabricated PH
hearing reports. Their private full reports/audio remain outside Git. Reuse them for identical bytes.

#### Retained failures and limitations

- During Q-02 USER reported a brief anomalous TTS sound. Same-run private observations show two
  leading colon characters in Q02's final LLM text, each admitted as a standalone TTS fragment with
  first PCM and playback completion. The following cleanup response also has leading punctuation.
  This supports a punctuation-only synthesis diagnosis, not an encoding-error claim or proven acoustic
  attribution. ASR retained the intended question; the substantive answer satisfies the Q02 factual
  rubric. All six declared Q criteria pass, but this separate audible-output finding is unfixed and
  must remain visible in delivery. USER explicitly defers this improvement to a later round; do not
  change the model, Reasoner, parser or TTS for it in this delivery. Locator:
  `quality-02/private/audible-artifact-observation.json`.
- The final Q interruption has no retained pre-reboot temperature or previous-boot journal. Current
  boot readings of 54.3–54.9 C and throttled=0x0 cannot establish the prior thermal/power state.
  systemd reports RuntimeWatchdogUSec=1min; current kernel logs confirm the hardware watchdog is
  active. This is a diagnostic lead, not proof of the reboot cause. No thermal, power, watchdog or
  application cause has been established; no stress test or configuration change was made.
- `manual-j2sg_ujx`: USER's short identity question led to 7.512429 s native decoding and 294 invalid
  UTF-8 bytes (incomplete final character), then ASR_TIMEOUT_UNPROVEN, ASR replacement and IDLE.
  Exact bounded input (26560 samples / 1.66 s) and full capture (2.5 s) both reproduce the decoder
  error offline. Original and 16x gain, no prompt and language-only prompt did not yield the correct
  answer; no tuning was promoted. Private locators: `debug-asr-failure-20261017`,
  `debug-asr-full-capture-20261017`, `debug-asr-level-20261017` and that run's prompt comparison.
- `debug-l1LSM5` / `debug-kv13g5`: prior ASR errors, no-input observer contamination and fatal cleanup
  failures remain FAIL. The apparent greeting came from an LLM answer to an incorrectly recognized
  input, not a new welcome cue. Actual USER recordings were reused privately rather than requesting
  repeated speech. The observer repair was demonstrated by before/after acoustic multi-Session runs
  `app-selfplay-session-20261017-h4ibdxcl` / `app-selfplay-session-20261017-shhn3gu8`.
- `asr-recovery-acoustic-20261017-01` crashed on capture close after a normal retry; the r10
  `acoustic-after` counterpart completed reminder/re-capture/IDLE and exit 0. It remained recognition
  INVALID because no usable endpoint was detected; successful cleanup is not recognition PASS.
- r10 `child-recovery-02` retained OPEN wire-state failure after ASR rebuild: old LLM Conversation was
  not closed. Repaired `child-recovery-04` completed replacement, new acoustic Session and shutdown.
  `child-recovery-03` was incomplete due an external diagnostic playback-task marking error; no
  product change was needed to correct that harness.
- r11 first `installed-entry-acoustic` failed before the first microphone frame with
  AUDIO_CAPTURE_FAILED, then `fault_recovery_key_mismatch` in Listen cleanup, exit 4. Original cause
  is unknown; do not infer a hardware fault. Input-ready-to-capture was 46.482 s versus 8.156 s in the
  later successful entry run: an observation, not a demonstrated cause. USER saw `audio`; independent
  owner-checked clear succeeded. Later success does not erase this explicitly deferred finding.
  No audio-fault voice notice is implemented or verified; ASR notice proof covers ASR faults only.
- `manual-hhg6svjf` logged two Sessions (14 and 4 response transitions), no warnings/errors and final
  IDLE at 23:52:16 +08. Pi rebooted about 23:54:39; no persistent previous-boot journal or normal final
  report exists. Native WAV/timing fragments survived; reboot/disconnect cause and pre-reboot thermal
  state are unknown. Post-reboot 54 C / throttled=0x0 do not explain the prior interruption.
- One r11 source/native probe overlapped Developer's large installation copy and had ~28 s THINK.
  Exclude it from performance conclusions. All later Pi transfer/install/tests/App runs are serial.
  The scoped diagnostic failures `acoustic-r1`, initial 50 s startup harness and source-attach races
  remain preserved; corrected harness runs, not discarded failures, establish the stated successes.

#### Performance disposition and remaining acceptance boundary

- USER accepted stopping further performance tuning after the two-Turn baseline at
  `<operator-home>/app-acoustic-20261012-r4/paired-01/`: one App/Session, two identical acoustic inputs,
  same backends, requests 1/2, exit 0 and owner release. Signal-end to first response write is
  **7.475216751 / 7.409803624 s**; native Whisper **3.745406 / 3.796533 s**, VAD tail **600 / 600 ms**.
  Receiving-to-THINK is **6.864078 / 6.909703 s**. No meaningful second-Turn ASR speedup is demonstrated.
  Signal end is waveform-aligned, not human audible end; first write is not measured acoustic onset.
  Second-Turn context/output differs, so this pair is not a statistical improvement claim.
- Prior formal PN blocks exist; PH's declared schedule/hearing report was incomplete after its earlier
  ASR/route mismatch. Free-use M and this acoustic pair cannot silently fill those missing PH rows.
  Preserve that boundary while delivering the bounded fixes; no new human schedule or Display-content
  gate is introduced here. Same-content final L/R/Q results are recorded in this closeout above.
- Next owner remains Developer for concrete failed checks, then Tester/Verify for remaining acceptance.
  Commit/push must describe delivered repairs and limits, not invent whole-ALPHA Accepted.

### ALPHA P／M development opened — 2026-10-11

- Entry: current.md opens the bounded P (PN／PH) and M package after completed Design／Test Spec.
  Baseline is delivered `19d9ca2`; the 2026-10-09 owner routing below is retained delivery context,
  superseded by this active package. No whole-ALPHA acceptance or commit is implied.
- Value/risk: lossless request-correlated timings prevent attributing first-response waiting to the
  wrong phase; real-time PCM prevents uncontrolled input delivery from confounding PN／PH comparison;
  revised Q fixtures prevent replaying retired questions. No optimization is selected before baseline.
- Estimate: 8 points for shared collection／parent-child boundaries, PN pacing／two-block runner,
  PH guide and fixture synchronization. Any one improvement is estimated only after supported diagnosis.
- Planned affected paths: `scripts/alpha_product.py`, `scripts/alpha_oracle.py`,
  `scripts/run-alpha-pv.py`, `src/sbd/cognition/observability.py`,
  `src/sbd/cognition/litert_lm/{adapter,worker}.py`, their directly affected existing tests,
  `scripts/run-app.sh`／`scripts/install_app.py` and their tests for entering the shared observer
  through the formal installed launcher, and this status. Actual collector gaps may require narrowly
  affected speech instrumentation.
- Test IDs: PN01–PN05／PH01–PH05; PN06／PH06 only for a recorded discrimination gap;
  ALPHA-Q01–Q06 fixture synchronization; M final-version real use remains separately identified.
- Workstation verification: `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/test_alpha_product.py tests/test_alpha_pv_runner.py -o addopts=''`, affected cognition tests
  when collection changes, syntax checks and `git diff --check`.
- Pi plan: isolated checkout of pending content, affected portable／integration tests with the Pi
  Python, exactly two fresh-App PN blocks and two fresh-App PH blocks before any improvement;
  900 s automatic／1800 s human watchdog and 20 s teardown. Exact new CLI commands will be recorded
  after implementation; existing P behavior is preserved. Final common-content L／R／Q／M remains pending.
- Execution order confirmed by USER: implement and check on workstation, then synchronize to an
  isolated Pi checkout for applicable verification before commit. USER will announce Pi readiness;
  do not connect again before that announcement. The previous alias-resolution failure is only an
  environment observation, not a reason to move development onto Pi.
- Authority precedence: USER／AGENTS.md forbids automatic source/config/model/evidence digests in
  tests/startup; older digest instructions in role/candidate documents are not applied. One independent
  transfer-boundary content comparison is performed only when needed.
- Implemented workstation scope: optional lossless private timing/count JSONL, actual parent send／receive
  and child receive／native-start／first-output／safe-text emit／terminal boundaries; PN real-time PCM,
  two fresh-App blocks and conditional matched controls; physical-input PH guide and same-observation
  hearing adjudication; formal installed launcher integration; revised `Q-20261011` fixture binding.
  PN／PH `VALID_OBSERVATION` is capture status only, not P completion, improvement or ALPHA acceptance.
- Pre-block observation limits: admission render begin／end is the existing MEASURE renderer, not native
  generation's internal rendering. Native render／prefill begin／end and distinct ASR endpoint are not
  exposed. Native callback first generated output is directly measured, not first native token. Human
  speech-end／acoustic onset remain NOT_MEASURED. Enclosing native-start→callback→safe-text and last
  microphone frame→ASR final are retained without invented internal phases.
- Count definitions: `input_tokens` = direct-user tokenizer count; `rendered_input_tokens` = rendered
  incremental tokens; `context_tokens` = KV tokens before this turn; `output_tokens` = native benchmark
  decode-token count. Request correlation includes private session／generation／request identity;
  each measured row matches the actual legacy native-start timestamp. Public contains only counts,
  booleans, case IDs and times. Startup prework means existing Engine setup and prompt token attestation;
  prior-inference reports observed GENERATE calls before IDLE, not hidden native internals.
- Pre-block precision: same Pi monotonic domain, integer nanosecond timestamps, actual clock resolution
  in the report; PN frames every 20 ms, no early frames, maximum 20 ms lateness/span error. Boundary-hook
  capture error has no supported bound yet: `capture_error_bound_ns=null`, timings descriptive,
  `improvement_claim_allowed=false`. No speedup claim can be made from these captures alone.
- Workstation focused checks: **282 Pass / 3 Linux-only deselected**, 4.33 s. Broader non-RPi selection:
  **1978 Pass / 1 Fail / 38 deselected**, 49.84 s; failure is existing R02-HEALTH's `/proc/meminfo`
  access on macOS, retained rather than relabeled. Syntax／shell syntax／whitespace checks Pass.
- USER announced Pi readiness. Candidate `/home/<operator>/alpha-pnph-20261011-d4Vxz8/repo`, base
  `19d9ca2` plus complete pending tracked patch, full Git history retained. Pi focused checks:
  **285 Pass**, 5.10 s (`<root>/focused-regression.log`); complete non-RPi suite:
  **1982 Pass / 35 deselected**, 58.65 s (`<root>/non-rpi-regression.log`). No Fail／Skip／XFail.
  One independent `rsync -nrcRi --from0 --files-from=<tracked-list>` found no tracked-content difference
  at the r1 transfer; subsequent observation-entry repair below requires its own Pi verification.
- Fixed 13-PCM binding prepared once with production TTS, `<root>/fixed-pcm/fixtures.json` and
  `fixture-metadata.json`; preparation log `<root>/fixture-preparation.log`. No LLM pre-test inference.
- PN command from `<root>/repo`: `<installed-python> scripts/run-alpha-pv.py --run pn
  --run-id ALPHA-PN-BEFORE-20261011-01 --installed-entry /home/<operator>/snowboard-app/run.sh
  --config <root>/product.local.yaml --fixtures <root>/fixed-pcm/fixtures.json
  --python <installed-python> --output <root>/pn-before-01 --phase before --watchdog 900
  --cleanup-timeout 20`. PH changes selector to `ph`, run ID/output to PH locators, watchdog to 1800.
  Conditional 06 is a separate two-block run with `--cause-control-reason <private hypothesis>`;
  do not enable without an actual discrimination gap. PH hearing report uses the same run with
  `--run ph --adjudicate <PH-output> --judgments <private-report.json>`; no product replay.
- M uses the final fixed entry with `ALPHA_TIMING_DIRECTORY=<fresh-0700-private-directory>`;
  the shared recorder retains parent/child timings and allowlisted runtime/timing dashboards while
  input and questions stay free. M segment, USER confirmation, actual exit status and release still
  require operator recording; no M PASS is inferred from PH or portable tests.
- Remaining: run PN／PH, retain full observations and interpret correspondence／causes; decide at most
  one supported improvement or NO_CHANGE; final-version M and final common-content L／R／Q Verify.
  No commit, push, performance claim or completed-P claim.
- PN r1 `ALPHA-PN-BEFORE-20261011-01`: **INVALID**, exit 2, `DRIVER_INCOMPLETE` before any voice
  stimulus. Actual App startup exit 2: strict configuration rejected `SBD_ALPHA_EXPERIMENT`.
  Block 2 is NOT_EXECUTED; result and private startup log remain `<r1-root>/pn-before-01/`.
  No product/native/hardware owner remained. Correct only experimental environment names to
  `ALPHA_EXPERIMENT`／`ALPHA_TIMING_DIRECTORY`, preserving the strict SBD config contract.
  Add regression through the formal launcher and real environment overlay. Preserve r1 source/release
  and evidence; create a new checkout/release/run ID for the repaired entry. This is instrumentation
  repair, not the package's one optional performance optimization.
- PN r2 `ALPHA-PN-BEFORE-20261011-02`: **INVALID**, `FRAGMENT_NODE_MISSING`. Block 1 completed
  all six real voice Turns and cleanup, but lacked every batch's `audio_first_write`; Block 2
  NOT_EXECUTED. The core resource is a VolumeControlledAudioOutput around ALSA, so the hook was
  attached above the native callback. Preserve all r2 observations/source/release at
  `/home/<operator>/alpha-pnph-r2-20261011-J3Vs9R/`; do not earn complete baseline credit.
  PN02 native-start→safe-text **13.476 s**, ASR-final→first-write **14.506 s**; PN04／PN03
  native-start→safe-text **1.976／2.197 s**. These are descriptive retained samples, not cause proof.
  r2 focused Pi regression **285 Pass**, 4.98 s; r2 transfer/deployment comparisons had no differences.
  Fix only the observation hook beneath the actual volume wrapper and test two separate batches
  with the real volume wrapper; use new source/release/run locator for affected PN baseline.
- Active r3 checkout: `/home/<operator>/alpha-pnph-r3-20261011-uRHDr0/repo`; installed release
  `/home/<operator>/snowboard-app/releases/pnph-observation-20261011-r3`, selected by the retained
  `~/snowboard-app/run.sh`. Older delivered repair and r1/r2 releases remain preserved. Fixed PCM
  is the original r1 binding via `<r3-root>/fixed-pcm`; no questions/audio regenerated after observations.
- r3 workstation directly affected runner/launcher/wrapper checks: **87 Pass / 3 Linux-only deselected**,
  1.15 s. Pi complete non-RPi regression: **1983 Pass / 35 deselected**, 55.98 s;
  `<r3-root>/non-rpi-regression.log`. Pi Python/shell syntax and whitespace checks Pass. Independent
  r3 transfer/deployment comparisons found no actual content differences; no product/source/test/runner
  changes occurred after these checks. Subsequent edits to this owner record describe results only.
- PN r3 `ALPHA-PN-BEFORE-20261011-03`: **VALID_OBSERVATION**, exit 0. Exactly two fresh-App blocks,
  each two Sessions/six voice Turns (four measured/two excluded close); no unexecuted cases. Required
  request/Turn/batch correlation, direct native observations and real-time PCM validity passed;
  both blocks have all product/process/hardware final-release booleans true. App is stopped.
  Public evidence `<r3-root>/pn-before-03/result.json`; private complete observations and per-process
  timing/dashboard JSONL under the sibling `private/`; outer log `<r3-root>/pn-before-03.log`.
  Same command as above with r3 root, `--run-id ALPHA-PN-BEFORE-20261011-03`, output `pn-before-03`.

| r3 PN case | Block 1 native-start→safe-text (s) | Block 2 native-start→safe-text (s) | Block 1 ASR-final→first-write (s) | Block 2 ASR-final→first-write (s) |
| :--- | ---: | ---: | ---: | ---: |
| PN02 fresh-App first Turn | 2.314925 | 2.296988 | 3.253033 | 3.183944 |
| PN04 same-Conversation follow-up | 1.903001 | 1.897801 | 2.553638 | 2.653576 |
| PN03 new Session, same engine/child | 2.185940 | 2.186723 | 3.131903 | 3.222388 |
| PN05 streaming | 1.913959 | 1.889188 | 2.603224 | 2.605796 |

- PN01 startup **4.620832／4.481774 s**. PN02/PN03 matched counts in both blocks: direct-user 6,
  context 0, rendered incremental 87, output 23 tokens. PN04 counts 7/111/15/20; PN05 9/111/17/29.
  PN05 yielded three fragments/two actual TTS batches in each block. Maximum observed frame lateness
  **4.202 ms**, below predeclared 20 ms validity limit. No average/best-of or rejected sample replacement.
- Retained r2 slow-sample localization: parent-send→child-receive **0.000100 s**,
  child-receive→native-start **0.000262 s**, native-start→first callback **11.990502 s**,
  first callback→child safe-text wire emit **1.495486 s**, wire emit→parent receive **0.000800 s**.
  r2 PN03 has identical direct-user/context/rendered counts 6/0/87 but native-start→first callback
  **0.824449 s**. This directly locates most waiting inside the native invocation before first output;
  it does not distinguish prefill, constraints, cache initialization or other hidden native phases.
- Latest complete r3 PN blocks **did not reproduce** the earlier slow first response: first-callback
  wait **0.944394／0.928840 s**. Fresh process alone is therefore not a sufficient explanation;
  fresh App does not promise cold OS/filesystem/native caches. No performance change was made between
  the retained slow r2 observation and fast r3 runs, so their difference is not an optimization benefit.
- Next owner remains Developer. USER directs automatic cause analysis to continue without waiting
  for PH; do not treat human availability as a prerequisite for focused diagnosis. Physical PH is
  still pending, and cannot be substituted with PCM. Planned PH locator:
  `ALPHA-PH-BEFORE-20261011-01`, `<r3-root>/ph-before-01`, same formal entry/config/runtime/collector,
  watchdog 1800 s and cleanup 20 s. Complete two fixed-script blocks, retain all hearing reports and
  compare common endpoints before choosing optimization disposition. PN06/PH06 is not enabled.
  M free-use and final same-content L/R/Q remain pending. P/ALPHA remain open; no commit/push.
- Focused native-wait diagnosis now authorized: distinguish Python response-format/argument preparation,
  synchronous native submission, and submission-return→first callback. Value/risk: the existing
  native-start stamp precedes those preparations, so attributing the whole 12 s to prefill may choose
  the wrong change. Estimate 2 points; affected paths `src/sbd/cognition/litert_lm/worker.py`, private
  timing allowlist in `observability.py`, existing native callback test, this record. Retain public
  protocol/model/prompt/input/settings; no optimization, pre-inference, OS reboot or cache mutation.
- Fixed deployed SDK `litert_lm/interfaces.py` exposes total engine/conversation init seconds,
  time-to-first-token seconds and the last prefill/decode token counts/rates. Collect these as native
  reported summaries; last count/rate gives a labeled derived duration, not begin/end stamps. The
  SDK's TTFT accessor is not yet proven per-Turn, so do not present it as each turn's interval or sum
  it with enclosing controller intervals. Native prefill begin/end remain NATIVE_NOT_EXPOSED.
- Before the next diagnostic stimulus, add format/optional-argument preparation boundaries and native
  call begin/end; capture first callback from the existing hook. Test on workstation, synchronize to
  a new Pi checkout/release, run affected regression, then exactly two fixed fresh-App PN blocks.
  Preserve r3 valid baseline and all r1/r2 failures. Additional repetitions require a new concrete
  discrimination question; do not retry until a preferred slow/fast outcome appears. USER stopped
  the M4 history inquiry; no further historical source is required for this analysis.
- USER confirms Pi was just booted before the retained r2 slow observation. Concrete remaining
  hypothesis: host-boot cold state versus App-process-first behavior. r3 fresh Apps were fast, so
  repeating arbitrary warm Apps cannot discriminate this. Prepare the same two-block PN schedule for
  the first App after a controlled Pi boot, then a fresh App on that same boot; retain fixed input,
  runtime/model/settings and no prior LLM inference. Host reboot has not been requested/executed yet.
- To make that prospective slow sample useful, also capture native-child cumulative major-page-fault
  and block-input counters at native submit and first callback, correlated to the same request. Their
  differences are narrowly scoped IO/page-in clues, not a generic CPU/memory/thermal survey or an IO
  duration assertion. Positive deltas alone cannot prove all waiting was disk IO. Affected paths stay
  worker/observation allowlist/native callback test; no cache clearing/model mutation or new Test ID.
- r4 native-stage implementation: workstation affected **218 Pass**, 3.54 s; Pi affected **286 Pass**,
  4.96 s (`/home/<operator>/alpha-native-r4-20261011-0qxvrW/focused-regression.log`). Independent
  transfer and deployment comparisons found no differences. New release
  `native-observation-20261011-r4`; previous releases remain preserved.
- r4 `ALPHA-PN-NATIVE-DIAG-20261011-04`: **VALID_OBSERVATION**, exit 0, both fixed fresh-App blocks
  complete; all final owner-release booleans true. Result/private data at
  `/home/<operator>/alpha-native-r4-20261011-0qxvrW/native-diag-04/`. No slow sample in this run.
  Native-start→first callback across all eight measured Turns **0.814193–0.972857 s**.
  Response-format setup **0.205592–0.236924 ms**; argument setup **0.047241–0.081963 ms**;
  native API call **1.482106–2.199160 ms**. All observed first callbacks arrived after that API
  returned. First-Turn return→callback **0.970696／0.932100 s**. These locate the warm-path wait;
  they do not prove the retained 12-second slow sample used the same internal split.
- r4 native benchmark: first-Turn derived last-prefill duration **0.795273／0.757561 s**.
  Actual TTFT report remained **0.902854／0.864681 s** on the following Turn of each Conversation,
  despite different directly measured callback waits, and changed on new Conversation. Treat it as
  the Conversation-first native summary in this runtime, never an independently measured per-Turn
  duration. No aggregate reported times are added to overlapping controller intervals.
- r5 IO-count addition: workstation affected **218 Pass**, 3.61 s. Preparing a new Pi candidate
  `/home/<operator>/alpha-native-r5-20261011-chETZR/` for the host-boot discrimination question;
  preserve r4 source/evidence, run applicable Pi checks first, and make the precise cold-boot command
  ready before requesting a host restart. Do not run more arbitrary warm PN blocks for this question.
- r5 standalone preparation suite: **1983 Pass / 35 deselected**, 55.94 s;
  `<r5-root>/non-rpi-regression.log`. It predates the following boot/CPU/Engine completeness additions
  and does not verify those later bytes. r5 has no new native run or selected installed release.
- Cold-boot collection refined before restart: private boot ID and App-start host uptime/wall time,
  direct child runtime/Engine begin/ready timestamps, existing Conversation/create-ready and all
  generation-preparation/submission/callback/safe-text boundaries; request-correlated cumulative CPU
  time (all LLM-child threads), major faults and block-input at submit/first callback. Public projects
  uptime and necessary counter deltas; boot IDs remain private. CPU can exceed wall time with multiple
  native threads, so do not interpret it as single-thread utilization or sum it with wall durations.
- New completeness checks reject missing Engine stamps, boot context, preparation boundaries or
  CPU/IO counters as diagnostic INVALID. Preserve counter before/after and native reported summaries
  privately. Distinct native prefill begin/end remain unavailable; count/rate-derived duration is
  labeled derived, and native TTFT stays a Conversation-first summary. No general resource survey.
- Affected scope for this refinement also includes `scripts/run-alpha-pv.py`, `alpha_oracle.py` and
  their existing tests. Workstation final focused selection: **285 Pass / 3 Linux-only deselected**,
  4.49 s; whitespace Pass. Preparing new r6 Pi checkout and full applicable suite. No reboot yet.
- r6 full Pi non-RPi suite: **1985 Pass / 35 deselected**, 56.24 s; candidate
  `/home/<operator>/alpha-cold-r6-20261011-u0HIIx/repo`, log `<r6-root>/non-rpi-regression.log`.
  Source and installed `cold-observation-20261011-r6` comparisons found zero differences;
  Python/shell syntax and whitespace Pass. Pre-boot reference and precise command prepared outside repo.
- USER now explicitly authorizes one Pi reboot and confirms no other users/workloads. USER also directs
  that subsequent experiment-only observation changes need no regression suite, and that each diagnostic
  run must test only the relevant question. Apply prospectively; no completed evidence is reopened.
- Focused cold-run schedule supersedes the pending full PN schedule for this cause question: exactly
  three real PCM/ASR/native LLM/TTS/Audio short turns, all `FX-SHORT-B` with empty Conversation context:
  first App/new host's first turn; same App/engine/child in a new Session; then one fresh App on the
  same host boot. Close each Session through the supported short Button callback after actual Audio
  completion, without extra voice-close questions, then supported App shutdown. No Q, follow-up,
  streaming or arbitrary repeated cases. This is diagnostic-only, not PN01–PN05 completion credit.
- Add `--diagnostic-first-use` to the existing `--run pn` entry; preserve normal PN behavior separately.
  Scope is experiment runner/oracle/stimulus helper and this status. Check syntax/whitespace and actual
  target capture validity; do not rerun portable regression solely for this observation helper delta.
  Prepare a new r7 checkout/release and fixed `ALPHA-NATIVE-COLD-20261011-07` command before reboot.
- r7 focused preparation: `/home/<operator>/alpha-focus-r7-20261011-urAGdg/repo`, installed
  `focus-observation-20261011-r7`, current fixed entry selects it. Workstation/Pi syntax and whitespace
  passed; one transfer comparison found no differences. No new regression run, per USER instruction.
- Authorized reboot executed once; private boot reference differs afterward. First App began at
  host uptime **42.989 s**, second at **97.716 s**, both on the same new boot with distinct App processes.
  Command from `<r7-root>/repo`: `<installed-python> scripts/run-alpha-pv.py --run pn
  --diagnostic-first-use --run-id ALPHA-NATIVE-COLD-20261011-07
  --installed-entry /home/<operator>/snowboard-app/run.sh --config <r7-root>/product.local.yaml
  --fixtures <r7-root>/fixed-pcm/fixtures.json --python <installed-python>
  --output <r7-root>/cold-focus-07 --phase before --watchdog 900 --cleanup-timeout 20`.
  First request had no preceding generation on that App/child; no other user/workload per USER.
- r7 **DIAGNOSTIC_OBSERVATION**, exit 0: exactly three short PCM→ASR→LLM→TTS→Audio Turns,
  supported Button Session close and App shutdown, all release booleans true. No extra voice close,
  Q, follow-up or streaming question. Both helper blocks VALID_OBSERVATION, none unexecuted. Public
  result `<r7-root>/cold-focus-07/result.json`, raw private data in sibling `private/`, outer log
  `<r7-root>/cold-focus-07.log`. Diagnostic-only result earns no formal PN01–PN05 completion credit.

| r7 same short input / empty Conversation | Cold first | Same engine, new Session | New App, same boot |
| :--- | ---: | ---: | ---: |
| Native-start→first callback (s) | 12.034470 | 0.832777 | 0.946605 |
| Native call return→first callback (s) | 12.019743 | 0.830767 | 0.944400 |
| LLM-child aggregate CPU delta to first callback (s) | 2.630148 | 2.647538 | 2.750422 |
| Major-fault delta | 1917 | 0 | 0 |
| Block-input delta | 1799744 | 0 | 0 |
| Native-start→safe-text (s) | 13.542481 | 2.210375 | 2.311703 |
| ASR-final→first Audio write (s) | 14.334911 | 3.151757 | 3.299428 |
| Derived native last-prefill duration (s) | 5.699157 | 0.728715 | 0.766344 |
| Derived native last-decode duration (s) | 8.784737 | 2.406175 | 2.466832 |

- All three rows have direct-user/context/rendered/output counts **6/0/87/23**, same fixed PCM and
  model/settings. Response-format setup **0.220–0.225 ms**, argument setup **0.065–0.082 ms**.
  Cold native API call **14.119 ms**, warm **1.495／1.587 ms**. Cold App startup **12.078 s**,
  Engine constructor **4.045 s**; warm fresh-App startup **4.626 s**, Engine constructor **0.319 s**.
  Conversation open **3.265／3.192／3.245 s**. This is not an App-first-only or context-token effect.
- Cold native reported TTFT **6.081 s** versus callback **12.034 s**: do not label the entire callback
  wait as prefill. Native reported prefill and decode both lengthened; callback includes later release
  beyond the native first-token report. Similar CPU deltas plus cold-only major faults/block input
  strongly support page-in/IO waiting rather than extra CPU computation. Per-file attribution is not
  yet directly measured; model versus packed-cache reads remain to distinguish before choosing a change.
- Relevant existing model-directory files: original model **2588147712 bytes**, XNNPACK weight cache
  **788412736 bytes**. Do not regenerate/delete cache, change model/runtime, force inference prewarm or
  claim the cache is absent. Inspect actual native Engine/Conversation mappings without generation,
  then use the smallest per-file observation needed to identify cold read source. App remains stopped;
  no product optimization or commit/push, P/ALPHA still open.
- Actual native mapping inspection without GENERATE confirms both files are mapped at Engine-ready
  and Conversation-ready: model seven regions/**2211381248 mapped bytes**, XNNPACK cache one region/
  **788414464 mapped bytes** (page-rounded). Private result `<r7-root>/cache-mapping-inspection-02.json`;
  zero generation requests, normal CLOSE/SHUTDOWN, child stopped. The first operator inspection omitted
  required CLOSE reason and failed; corrected only that operator command, retained tool failure, did not
  rerun product questions or edit product code. Mapping presence alone does not identify IO attribution.
- Next focused cause experiment: after a new controlled host boot, read only the actual mapped
  **788412736-byte XNNPACK cache** sequentially once, leave original model bytes unread by the operator,
  then run one same short/empty-context first request. Compare native wall/CPU/fault/block-input and
  reported prefill/decode with r7 cold sample. Record pre-read duration separately from App startup and
  process-start→first Audio write; it is not a claimed speedup or a product prewarm/optimization.
  Cache content/model/runtime/settings remain unchanged; no inference occurs during pre-read.
- Value/risk: targeted cache-only intervention distinguishes packed-cache cold reads from the broader
  model/IO hypothesis. Cost: one read and one short real native Turn, no Q/full PN/regression replay.
  Add experiment-only `--diagnostic-single-request` on `--diagnostic-first-use`; scope scripts driver/
  runner/oracle plus status, estimate 1 point. Syntax/whitespace and actual capture validity only per USER.
  This is cause discrimination, not the package's one optional product optimization. Preserve all r7 data;
  new checkout/release/run locator for this helper delta. USER's host-reboot authorization remains in scope.
- r8 cache-only intervention: `/home/<operator>/alpha-cache-r8-20261011-w0Devn/`, source helper adds
  `--diagnostic-single-request`; syntax/whitespace and one transfer comparison passed, no regression
  replay per USER. One controlled reboot, then cache-only sequential read, then exactly one short native
  Turn with Button Session close/shutdown. `ALPHA-CACHE-PRELOAD-20261011-08` is
  **DIAGNOSTIC_OBSERVATION**, exit 0, all capture/release conditions true. Public/private result at
  `<r8-root>/cache-preload-08/`; pre-read/residency observations `<r8-root>/cache-preload-observation.json`.
- Non-faulting `mincore` confirmed before pre-read: model/cache **0/0 resident pages**; after pre-read:
  original model still **0**, cache **48121/48121 pages** resident, page size **16384 bytes**.
  Only cache bytes **788412736** were read, taking **8.364313 s**. Neither model nor cache content changed;
  no operator model-data read or generation preceded the first request.
- Same input/context/rendered/output counts **6/0/87/23**. Native-start→callback **2.769164 s**
  versus retained cold **12.034470 s**; CPU **2.773745 s**, major faults **1117**, block input **260288**
  versus **2.630148 s / 1917 / 1799744**. Derived prefill/decode **2.581636/2.617829 s** versus
  **5.699157/8.784737 s**. ASR-final→first Audio write **5.421345 s** versus **14.334911 s**.
  This cache-specific intervention supports packed-weight cache cold page-in as the dominant first-output
  delay; residual IO remains and is not falsely attributed entirely to cache or CPU.
- Pre-read is not a performance fix: App startup **12.124196 s**, process-start→first Audio write
  **27.583085 s**; adding the separate pre-read gives **35.947398 s**, versus original **36.447726 s**.
  Single-sample near equality and unsupported capture-error bound cannot support a total speedup claim.
- USER asks whether pre-read is possible. Select one bounded product experiment supported by the cache
  intervention: optional engine-owned background read of the already-mapped cache, launched at first
  Conversation OPEN, overlapping the measured ~3.2 s Conversation construction plus PCM input/ASR time.
  No fake inference, model change, cache creation/deletion or blocking pre-read gate.
- Predicted affected nodes: fewer cache IO faults between GENERATE and first callback, shorter first
  ASR-final→Audio and process-start→first Audio without equivalent added startup wait. Cost/risk:
  one small read buffer/thread, disk contention may slow ASR, stop must cancel/join the reader and close
  its FD; these are the direct functional/lifecycle risks to test. Estimate 2 points. Affected paths:
  worker implementation, private observation allowlist, experiment flag forwarding in alpha driver/runner,
  existing native/worker tests and this owner record. Keep public LLM API, protocol, timeouts and profile.
- Check only affected prefetch completion/cancellation/no-file behavior and existing directly affected
  native worker/streaming tests on Pi, then one cold same-short-input product run with the feature enabled.
  No full question set or regression suite; observation-only follow-ups still skip regression per USER.
  Record all prefetch begin/end/cancel/fail outcomes and startup/ASR/first-audio costs. This is the one
  optional product optimization trial; ineffective/regressing behavior is rejected, no second trial here.
- USER explicitly requests formal solution, implementation and completed testing, then remaining PN/PH
  against the retained solution. Formal design stays inside ALPHA's one bounded improvement contract:
  default first-OPEN background read of the one already-mapped XNNPACK cache, once per Engine; no new
  public API/config flag and no startup/inference wait. Failed/unavailable cache read retains the original
  generation path. Conversation close retains engine-owned reading; Engine shutdown cancels/joins it,
  closes the file and then destroys Engine. Parent force-termination remains the existing final fallback.
- Test mapping before implementation/Verify: existing native worker/prompt/streaming suites plus four
  direct risks: complete read leaves file unchanged and starts once; missing-file IO fallback; shutdown
  cancels the read and closes FD; Runtime's first OPEN launches without waiting and later OPEN does not
  duplicate the reader. All are actual implementation tests, no new generic closure or hashing assertions.
  Pi cold one-short-question integration checks prefetch start/end versus first GENERATE, context/schema/
  ASR/TTS/Audio/stop/release, startup and speech-end/ASR/first-audio costs. Then final PN01–PN05/PH01–PH05
  according to existing Test Spec, reusing applicable final-content data; no retired P/Q replay.
- Implemented `WeightCachePrefetch`: one read-only 1 MiB buffer, one non-daemon Engine-owned thread,
  captured OPEN identity for complete correlation, one attempt per Engine, normal fallback on IO failure.
  Stop checks cancellation between chunks and bounded join; does not modify LLM/public protocol or timeout
  settings. Private observations identify completion/cancellation/failure without file contents/paths.
- Workstation native/prompt/wire/streaming affected selection after reader code: **199 Pass**, 3.17 s;
  newest prompt/reader/Runtime integration selection **43 Pass**, 0.15 s. Syntax/whitespace Pass.
  Prepare r9 new Pi checkout/release; run only directly affected tests and focused native integration,
  preserving r7/r8 diagnosis/source. Final formal PN/PH use this retained implementation after convergence.
- r9 same-content Pi checkout `/home/<operator>/alpha-prefetch-r9-20261011-RYHsb5/repo`, selected installed
  release `/home/<operator>/snowboard-app/releases/prefetch-20261011-r9`. Directly affected Pi native/wire/
  streaming checks **200 Pass**, 3.82 s; `<r9-root>/affected-regression.log`. Python/shell syntax,
  whitespace and independent tracked-file transfer comparison passed. The r9 installed entry uses the
  original product runtime/model/config APIs with only the private experiment log path redirected.
- Cold boot diagnostic `ALPHA-PREFETCH-COLD-20261011-09` is **INVALID**, `PACING_DISTORTED` before ASR
  or GENERATE; preserve `<r9-root>/prefetch-cold-09/` without retrying under that ID. The cache reader
  started during first OPEN. Fixed PCM frame 10 was delivered **75.527 ms** late against the declared
  20 ms bound, so this run cannot demonstrate a first-response benefit. Startup/native timing and the
  partial pacing record remain diagnostic only. A cold product benefit is still unproven; disk/resource
  competition during concurrent pre-read is a live risk, not a proven cause of that one late frame.
- Formal same-content PN `ALPHA-PN-AFTER-20261011-09`: **VALID_OBSERVATION**, exit 0, exactly two
  fresh-App blocks with PN02/04/03/05 and two excluded voice closes each, all Turn/cleanup criteria
  Pass. Public `<r9-root>/pn-after-09/result.json`, full private observation/timing/dashboard files
  under its `private/`. Both blocks include cache start and complete, before first GENERATE; reader
  completed in block 1 in 4.080 s. Real-time PCM max lateness across counted Turns was 1.19 ms.
  PN02 native-start→first callback **2.771851／0.938319 s** and ASR-final→first Audio write
  **5.199270／3.137593 s**; the first block retained residual major faults
  despite cache completion. Do not claim cold-boot improvement from these same-boot PN blocks, and do
  not treat `VALID_OBSERVATION` as P acceptance.
- Collection scope for later felt-delay analysis: App/Engine startup, Conversation OPEN, input frame
  pacing, last captured frame→ASR final, parent/child/native LLM boundaries, first safe text, TTS
  first PCM, actual Audio write/completion, plus native CPU/major-fault/block-input counters and cache
  reader begin/end are recorded per correlated Turn. Native internal render/prefill timestamps, ASR's
  internal endpoint, human speech end and speaker acoustic onset are unavailable; those intervals are
  labeled rather than inferred. The r9 cold invalid observation shows pacing must be checked before
  comparing timing. PH is still required for human-perceived wait and speech quality.
- PH physical-input helper on Pi: `<r9-root>/run-ph.sh` (shell syntax checked, mode 0700), using the
  same installed entry and r9 bytes, output `<r9-root>/ph-after-09`. It prints each Button/utterance/
  shutdown cue; no PCM substitution or automatic hearing judgment. USER physical execution and the
  eight hearing rows remain pending. No commit, push or whole-ALPHA conclusion.
- A second independent cold reboot with unchanged r9 bytes, `ALPHA-PREFETCH-COLD-20261011-10`, also
  ended **INVALID/PACING_DISTORTED** before ASR or GENERATE: fixed frame 10 arrived **87.181 ms** late.
  Cache pre-read had started and not ended in both r9 cold observations. Preserve both invalid runs;
  they expose a repeatable cold-start resource-contention risk without proving its exact scheduler cause.
- Refine the same cache-reader trial by lowering only its Linux thread CPU priority and I/O class to
  idle; failures to set priority preserve the original read fallback. This is a targeted remedy for
  disrupting foreground capture, not another performance trial. Workstation and Pi directly affected
  native/wire/streaming tests each **200 Pass**; r10 checkout
  `/home/<operator>/alpha-prefetch-r10-20261011/repo`, release
  `/home/<operator>/snowboard-app/releases/prefetch-20261011-r10`; independent tracked-file transfer check
  found no difference at this point. Pi log `<r10-root>/affected-regression.log`.
- r10 new cold boot focused one-request `ALPHA-PREFETCH-COLD-20261011-11`: **DIAGNOSTIC_OBSERVATION**,
  inner block **VALID_OBSERVATION**, normal shutdown. All 133 real-time PCM frames were valid;
  maximum lateness **6.489 ms**. Cache pre-read completed its 788,412,736 bytes in **8.876 s** before
  GENERATE. Native-start→first callback **2.765636 s**, ASR-final→first Audio write **5.202723 s**,
  process-start→first Audio write **27.344184 s**; native request still had 1117 major faults and
  260288 block-input units. Preserve `<r10-root>/prefetch-cold-11/`; one cold sample supports a
  local reduction in first-output waiting against retained r7, but cannot establish a general speedup
  or eliminate residual page-in.
- Formal same-content r10 PN `ALPHA-PN-AFTER-20261011-10`: **VALID_OBSERVATION**, exit 0, two fresh
  installed-App blocks, all six Turns per block Pass and clean shutdown, all required correlated phase
  observations present. Public `<r10-root>/pn-after-10/result.json` and complete private source records
  under its `private/`. PN02 native-start→first callback **0.941／0.932 s**; cache read completed before
  GENERATE in both blocks. Maximum counted PCM lateness **1.213 ms**. This confirms warm same-content
  operation; the separate valid cold one-request diagnostic above supplies cold-start evidence.
- PH helper was updated to `<r10-root>/run-ph.sh` (shell syntax Pass, mode 0700) with r10 installed
  release/config and `ALPHA-PH-AFTER-20261011-10` output `<r10-root>/ph-after-10`. PH's two fresh-App
  blocks and eight physical hearing rows were pending USER execution. No commit/push or whole-ALPHA
  conclusion; M free use and final same-content L/R/Q Verify remain separate.
- USER executed the r10 physical PH. `ALPHA-PH-AFTER-20261011-10` is **INVALID/DRIVER_INCOMPLETE**;
  PH02 completed and PH04 began, then App exited fatal with `AUDIO_CAPTURE_FAILED` at the second
  capture. PH03/PH05 and block 2 were not executed. Public `<r10-root>/ph-after-10/result.json`,
  private observation and App log are retained; no hearing result is inferred. The PH observation
  wrapper iterated the live ALSA stream but did not close that inner stream when ASR stopped early,
  leaving AudioInput active for the next Turn. Repair only the wrapper with `aclose()` in a `finally`;
  add a two-Turn early-stop resource test, then verify affected code on Pi and create a new append
  r11 checkout/release/run ID for PH. Do not ask USER to repeat the invalid r10 script.
- r11 PH wrapper repair closes the real inner microphone stream in `finally` when the listener
  closes the outer observation stream. A direct two-Turn early-ASR-stop test proves the second
  capture can open after the first closes. Workstation PH probe selection **23 Pass**; the combined
  macOS runner selection had **74 Pass / 3 Fail** solely in existing `/proc`-dependent Linux tests,
  which were rerun on Pi. Pi affected product/runner selection **77 Pass**, 1.04 s, log
  `/home/<operator>/alpha-prefetch-r11-20261011/affected-regression.log`. The new checkout and selected
  release are `<r11-root>/repo` and `/home/<operator>/snowboard-app/releases/prefetch-20261011-r11`;
  independent tracked-file comparison and shell syntax passed. Physical PH helper is
  `<r11-root>/run-ph.sh`, new output `<r11-root>/ph-after-11`; no result exists yet.
- After the r10 fatal, USER observed the OLED still showing the last frame. Pi process and audio-owner
  inspection found no App/child or ALSA owner: `run_app` intentionally skips the normal RM/display
  clear path for `EXIT_RUNTIME_FATAL`, and SSD1351 retains its last pixels. An isolated r11
  `DisplayDriver.start → clear → show → stop` command exited 0 and released SPI; subsequent process/
  SPI-owner inspection was empty. This operator screen reset does not turn invalid r10 PH into a pass
  and does not change product source. The repaired PH will exercise normal shutdown.
- USER executed r11 physical PH `ALPHA-PH-AFTER-20261011-11`: **FAIL/SESSION_ENDED_BEFORE_FIXTURES**.
  Session A PH02/PH04/normal close all completed. New Session B PH03 entered with a different Session
  identity and zero prior KV tokens, but actual ASR decoded `1月星期有幾天。` for the fixed spoken question;
  native response routed END_SESSION rather than KEEP_NEXT. Thus PH05, the second close and block 2
  were not executed. Preserve `<r11-root>/ph-after-11/` and its exact route/ASR record; do not relabel
  the Turn or claim a PH pass. App exit was 0 and ALSA/display/hardware owners were released; public
  `stopped_cleanly=false` reflects incomplete test driver, not a surviving App. An append run helper
  `<r11-root>/run-ph-12.sh` uses unchanged r11 product bytes and new ID/output
  `ALPHA-PH-AFTER-20261011-12` / `<r11-root>/ph-after-12`; USER must physically speak the unchanged
  prescribed script. No question/fixture, route, ASR or product setting is changed.
- USER pauses further PH execution and prioritizes the felt delay from WAKE/`準備中` through live
  `接收中`. Current records must use correct boundaries: `last_frame→asr_final`, not microphone-start→
  result or pure Whisper runtime. Across 24 distinct r3-before/r10-after PN Turns (including excluded
  close Turns), known fixed-PCM last nonzero speech frame→last received frame is **0.540–0.621 s**
  (mean **0.561 s**), consistent with the fixed 600 ms VAD endpoint rule but not an exact human
  speech-end measurement. Last received frame→ASR final is **3.665–3.968 s** (mean **3.788 s**);
  four distinct r11 live PH Turns are **3.716–3.766 s**. For analysis label the latter ASR
  post-capture/return time; endpoint-event, WAV/IPC and native transcription begin/end were not
  stamped, so do not call the whole interval native inference.
- Targeted M4A comparison: existing Pi `M4A-ASR-001` accepted card in
  `docs/outsource/evidence/M4A-TESTER-6C3BA954-20260829/m4a/target/cards/` reports
  **3535.366 ms** and M4A-ASR-002 reports the same maximum for two Turns. The M4A test's helper
  times `asr.transcribe(_pcm_frames(path))` from call to returned result and feeds its PCM without
  real-time pacing. It is similar in scale to the current ~3.8 s post-last-frame interval but is
  not the same metric; no historic result is rewritten or reopened.
- Focused live-speech diagnostic design (observation only, before any endpoint tuning): one fixed
  short utterance spoken through the real microphone, optionally repeated once if speech/noise is
  ambiguous. Retain the same input frames with 20 ms delivery timestamps in private memory and write
  the short audio only after timing capture; annotate the final audible syllable on the waveform as an
  independent human speech-end estimate with annotation uncertainty. Record request-correlated VAD
  first possible end, confirmed end/ENDPOINT, Whisper transcription begin/end and ASR result receive
  using the Pi monotonic clock, without transcript/PCM in public evidence. Compare human end→ENDPOINT
  and ENDPOINT→result, reporting annotation uncertainty and distinguishing VAD proxy from acoustic end.
  The existing fixed PCM supplies a control with known last nonzero frame; no full PN/PH rerun or
  latency threshold change is needed. Value: resolve whether apparent live waiting is before or after
  endpoint; risk: a human stop marker inferred from VAD itself would be circular, while synchronous
  disk writes during capture could distort latency. No experiment source is implemented yet.
- USER item 5 — cache reader status: default first-OPEN pre-read and lower-priority reader are
  implemented. Their directly affected Pi tests passed; one r10 cold short-Turn diagnostic and two
  r10 fresh-App PN blocks were valid. This is completed focused engineering verification of the cache
  change, not completion of the whole P/ALPHA acceptance or proof of a general speedup. The later r11
  change is limited to the PH observation wrapper and passed its affected Pi tests; it does not require
  repeating PN solely to verify the unchanged cache reader. Remaining package work is a complete valid
  physical PH observation with hearing adjudication, final-version real-use M and common-content
  L/R/Q Verify before commit. The r11 PH run ended early on an ASR/route mismatch, not a cache failure.
  No commit or push.
- USER item 6 — a short voice cue after `準備中` is retained for later product discussion. It has not
  been designed or implemented and is outside the current cache/ASR diagnostic.
- USER six-item disposition: **1 closed as a measurement definition**, with ~3.8 s meaning last
  captured frame→ASR result rather than capture start→result; **4 closed as the targeted M4A
  comparison**; **5 closed for cache implementation and focused Pi verification only**. These closures
  do not assert whole-P/ALPHA acceptance. **2 remains open** for the discrepancy between fixed-PCM
  endpoint behavior and perceived live waiting; fixed PCM does not establish human speech end.
  **3 remains open** for the one-utterance live-speech timing experiment above. **6 moves to the next
  product discussion** and is outside this experiment. The active diagnostic scope is only 2+3.

### Developer delivery scope and next owner — 2026-10-09

- USER requested delivering this Developer iteration first, then Designer planning the next
  performance improvement round, and deciding ALPHA closure afterward. Deliver the tested fixed
  terminal installation and interruption/restart/stop repair; do not claim ALPHA Accepted, create
  a completion tag or run a service/optimization as a prerequisite for this delivery.
- Iteration verification is not skipped: Pi portable regressions, real native interruption/restart
  checks, fixed-entry startup/stop and USER live retest are recorded below. Final whole-ALPHA
  acceptance Verify is deferred, not relabeled as PASS or spliced from older candidates.
- Prompt correction is already in WIP `9c13509`: `明確要求對話結束時`, counts 59/9/68. No new
  prompt change is pending in this iteration. Designer must reconcile existing authority and
  Test Spec with the measured wording/fixtures and USER's retired-question/quality decision;
  retain original FAIL observations. Synchronization is feedback, not another approval gate.
- Next owner after this delivery: Designer for one bounded performance work item. Primary
  observation is slow first response (most recent live ASR-final → first-audio 13.333 s,
  LLM-send → first-safe-text 12.762 s). Later native-generation Turns are faster, but cause and
  stable improvement are unproven. Fix timing retention before drawing optimization conclusions:
  text logging truncates rows, human speech end is missing, and first audio write is not an
  acoustic perception timestamp. Preserve privacy and measure the selected before/after path.
- Existing `docs/status/current.md` and `docs/status/design.md` remain Designer-owned and were
  not modified. Handoff is this existing owner record plus the USER reply, not a new summary file.
- Pending commit is an append-only Developer delivery after WIP `9c13509`, not an amendment,
  ALPHA closure or authorization to push. Full subject/body/file approval is required below.

### Interrupted-session repair result — 2026-10-09

- USER requested fixing the reproduced failures. Value/risk: after a real Button interruption,
  backend cleanup must complete or report destroyed resources for RM recovery before a new
  Session; final stop must tolerate already-terminated TTS without a false stop failure.
- Estimate: 3 points. Affected paths: `src/sbd/action/speak/streaming.py`,
  `src/sbd/cognition/reasoner.py`, `src/sbd/action/speak/matcha/adapter.py`,
  `tests/test_alpha_interrupt.py`, `scripts/check_interrupt.py` for targeted native regression,
  `scripts/install_app.py` / `tests/test_app_install.py` for the fixed-entry release selector,
  narrowly affected streaming tests if required, this status.
  Preserve public APIs, lifecycle timeout values, schema, prompt, admission and fault taxonomy.
- Repair plan: keep the PCM consumer alive for typed TTS cancellation, complete repeated cleanup
  instead of equating CANCELLED with already-clean; forced cleanup bypasses graceful wait and
  returns actual destruction keys. Reasoner owns provisional streaming cleanup before Speak
  adoption, including a durable cleanup hook after a cancelled outer call. Matcha stop is
  idempotent for a child whose STOPPED/DESTROYED cleanup already completed.
- Verify plan: convert the two diagnostic reproductions to graceful/forced-recovery regressions,
  affected portable integration tests on workstation/Pi, real native backend interruption/restart
  and shutdown on a new Pi candidate with private logs, then install a new fixed-entry revision
  without rewriting earlier tested product source or evidence. USER's old quality questions are
  not replayed. No commit or final whole-ALPHA acceptance is implied.
- Implemented and verified: StreamingSpeak keeps its native TTS terminal consumer alive through
  typed cancellation; repeated cancellation finishes pending cleanup. Level 2 bypasses graceful
  waiting and reports destruction. Reasoner clears its provisional streaming owner and preserves
  the forced-cleanup hook even after an outer call finishes. Matcha stop accepts an already
  STOPPED/DESTROYED owner without attempting another READY-only shutdown.
- Workstation affected regression: **159 Pass**, exit 0. Pi same affected selection: **159 Pass**,
  exit 0, 1.65 s. Complete Pi non-RPi regression after the core fix: **1967 Pass / 35 deselected**,
  exit 0, 61.56 s; no Fail/Skip/XFail. The later installer selector adds one test, covered in the
  final Pi deployment/interruption/launcher selection: **18 Pass**, exit 0, 0.58 s. Do not label
  that later selector as included in the earlier complete suite.
- Candidate: `/home/<operator>/alpha-interrupt-fix-20261009-PluRne/repo`, WIP `9c13509` plus
  pending changes. Logs: `<root>/focused-regression.log`, `non-rpi-regression.log`,
  `deployment-regression.log`. New fixed diagnostic PCM was prepared once from two camping/
  encouragement stimuli, not the retired Quality questions; mapping `<root>/fixed-pcm/fixtures.json`.
- Actual Pi native backend regression passed: `provisional-01/result.json` proves interruption
  in THINK with a safe fragment admitted and real TTS BUSY; `playback-02/result.json` proves
  interruption in ACTION after ALSA's first positive audio write with playback still active.
  Both prove old work/control/queues cleaned, TTS and recovery READY before new admission, a new
  Session completing real ASR → LLM → TTS → Audio, normal close and exit 0, zero stop failures,
  and no remaining child/audio/display/hardware owners. No substitutes for LLM/TTS/Audio were used.
  Input is controlled new PCM through `AudioInput.frames`, and Buttons use the production GPIO
  callback; this native regression is not a second live-microphone human judgment.
- Native `playback-01` is retained as a failed/ineligible observation: the initial helper read a
  timing node emitted only after completion, so it never observed active playback or injected
  the intended Button. App later hit WorkerContractViolation during unscheduled capture; exit 4,
  cleanup booleans false at the snapshot. Later inspection confirmed process/fd release. Corrected
  only the helper's playback detector to the actual live ALSA write flag, without changing product
  source/config/PCM, then obtained the separate `playback-02` Pass. Never relabel the first result.
- Deployed fix as `/home/<operator>/snowboard-app/releases/interrupt-fix-20261009` with `current`
  pointing there. Original installed source/model/runtime/config and original entry bytes remain
  preserved; only fixed-entry routing changes. `~/snowboard-app/run.sh` still needs no arguments.
  New release uses the stable shared runtime/model/audio products; no test-directory dependency
  is introduced into normal operation. Future fresh installer supports the same release selector.
- Fixed-entry smoke reached clean IDLE, then terminal Ctrl+C exited **0** with no product/native
  child or hardware holder; `<root>/installed-fix-startup-01.log`. App is stopped; Pi stays online.
  USER saw standby during this operator startup check, not a hung second-Session attempt.
- Independent transfer-boundary comparisons found no differences across nine modified source/
  installer/helper/test files in the Pi checkout, nor installed release `src`/`requirements`/launcher
  (caches excluded). Syntax, compile, whitespace and changed-file privacy checks Pass.
- USER completed two rounds through the fixed entry and long-pressed to close the repaired App.
  Latest launch reached IDLE at 17:51:31 +08:00. First speaking Session had two Turns, including
  ACTION → IDLE at 17:52:20; the new Session began at 17:52:23, completed further voice Turns,
  and returned PERCEPTION → IDLE at 17:53:27. A brief final WAKE/PERCEPTION sequence occurred
  before return to IDLE at 17:53:35 during the reported final close; it is recorded, not silently
  counted as a third completed voice test. Latest-launch ERROR/CRITICAL count **0**, WARNING **0**.
  Follow-up inspection found no repaired App/native child or capture/playback/SPI/GPIO holder.
  USER terminal exit status was not retained, so no independently measured exit-0 claim for this
  human run. Pi is still online; App is stopped. Human interruption/restart/close retest is complete.

| Repaired live Session / Turn | ASR final → first audio write (s) | LLM send → first safe text (s) |
| :--- | ---: | ---: |
| S1 / T1 | 13.333 | 12.762 |
| S1 / T2 | 3.021 | 2.202 |
| S2 / T1 | 2.985 | 2.089 |
| S2 / T2 | 1.966 | 1.533 |
| S2 / T3 | 0.683 | unavailable |
| S2 / T4 | 2.140 | 1.555 |
| S2 / T5 | 2.376 | 1.680 |

- The same existing 512-character truncation and missing physical speech-end limitations apply.
  S2/T3 has no surviving LLM-send/safe-text nodes and cannot earn fast-generation credit.
  Interrupted S1/T2 first-audio time does not prove a full audio drain. First-response latency
  remains visible and unoptimized; repair success is functional, not a performance improvement.
- Next: Developer completes final common-candidate ALPHA Verify and measured scope/prompt feedback
  to existing design/Test Spec owners. Native/portable repair verification and repaired-version
  human retest are complete; original failure findings below are preserved provenance, superseded
  by this resolution. Do not replay retired Quality questions or infer formal ALPHA acceptance.
  No commit, push, service change or performance optimization was performed.

### Pre-fix focused interruption debug record — 2026-10-09

- USER requested actual debug rather than hypothesis-only reporting. Value/risk: reproduce a
  second Session rejected after interruption and distinguish streaming-owner leakage from model
  quality. Estimate: 1 point for reproduction. Affected path: `tests/test_alpha_interrupt.py`
  plus this status; production source is not modified in this diagnostic step.
- Plan: real Reasoner/WorkerRuntime/StreamingSpeak/Matcha adapter cancellation path with a
  controlled child protocol seam; deadline interruption during TTS receive; then a second real
  Reasoner turn. Separately reproduce repeated TTS stop after forced termination using the real
  FramedProcess state check. Run on workstation and Pi; no native input replay, debugger attachment
  to the live App, forced shutdown or old quality questions. A diagnostic Pass means defect
  reproduced as asserted, not product behavior accepted.
- Executed on workstation: **2 diagnostic reproductions Pass**, exit 0, 0.18 s. Reproduced
  cancelled streaming control still claimed after timed-out Reasoner abort, then a second turn
  raising `RuntimeError("streaming Speak operation already active")`, projected as `LLM_UNEXPECTED`.
  Separately the actual Matcha adapter/FramedProcess state path reproduced BUSY stop → DESTROYED
  → repeated stop rejecting non-READY state. The second reproduction creates no native subprocess.
- Same two tests on Pi: **2 diagnostic reproductions Pass**, exit 0;
  `/home/<operator>/alpha-launcher-20261009-x1EXAr/interrupt-debug-01.log`.
  Both execute product classes, but use controlled child/LLM seams; they are not a native microphone
  replay or proof of the live exception traceback. The live symptom's stage/code and reproduced
  failure mechanism agree. No production fix or installed-source change is claimed yet.

### Interrupted Session restart finding — 2026-10-09

- USER attempted another interrupted-session test and reported the second round stuck. No
  operator button, replay, shutdown, restart or code mutation was performed during inspection.
- Latest installed launch reached IDLE at 17:14:55 +08:00. One completed ACTION → PERCEPTION
  was followed by a second THINK, then THINK → IDLE at 17:16:13. Second physical Button was
  received (IDLE → WAKE at 17:16:15), real ASR completed (PERCEPTION → THINK at 17:16:25),
  then `LLM_UNEXPECTED`, UNPROVEN LLM resource, occurred before any LLM-send/first-safe-text/
  first-audio timing node. Current run is a failed second-Session response, not an unreceived Button.
- Fault entered ERROR, replaced the LLM child once as observed in the process/log snapshots,
  and returned to IDLE at 17:16:25.991. Main App, ASR and TTS were still alive; replacement LLM
  PID was 4100. Therefore latest observed state is recovered standby, not a permanently stuck
  TTS playback. USER-visible output/Display confirmation remains separate from log evidence.
- Important boundary: logged first interruption was THINK → IDLE, not ACTION → IDLE. It does
  not reproduce the earlier speak-abort/long-press TTS shutdown sequence exactly. Do not assume
  both incidents have the same cause. Error projection retains only a stable code, not the
  underlying exception detail; exact cause of LLM_UNEXPECTED is not established yet.
- Source diagnosis points to the streaming-control creation/release boundary as one candidate:
  a new turn can prepare admission successfully and then fail before GENERATE if the previous
  StreamingSpeak control remains claimed. This needs a targeted reproduction, not an inference
  presented as proven. Previous live error/raw records remain in the installed private product log.
- Next owner: Developer for focused interruption/restart diagnosis. Do not mark ALPHA function
  convergence complete while the confirmed second-Session failure and TTS shutdown finding remain
  open. No final Verify, new quality questions, service change or performance optimization occurred.

### USER-operated installed-entry test — 2026-10-09

- USER ran `~/snowboard-app/run.sh` and reported completing one round. Latest installed-log
  startup reached IDLE at 17:02:11 +08:00; first Button trigger at 17:02:21. Observed nine
  THINK → ACTION entries, eight ACTION → PERCEPTION continuations, then ACTION → IDLE at
  17:04:40. Exact audible/semantic assessment and the final physical/terminal stop action are
  not yet confirmed; do not label all nine actions clean completions from transitions alone.
- Latest launch contains **one ERROR and two WARNING** rows: speak Level-1 abort timeout at
  17:04:39, TTS stop warning at 17:04:44 (`clean shutdown is legal only from READY`), followed
  by a resource-stop error for `backend.action.speak.tts`. Older installation fatal remains
  preserved separately. The raw private trace is in `~/snowboard-app/logs/application.log`.
- Follow-up inspection found no installed App/LLM/ASR/TTS process and no capture/playback/SPI/GPIO
  hardware holder. App is stopped and Pi remains reachable. USER launch did not retain an exit
  status, so no exit-0 claim. This live shutdown finding is open even though no owner leaked.
- Retained timing nodes from this launch (seconds):

| Turn | ASR final → first audio write | LLM send → first safe text |
| :--- | ---: | ---: |
| 1 | 13.999 | 13.379 |
| 2 | 2.758 | 1.993 |
| 3 | 0.749 | unavailable |
| 4 | 2.634 | 1.988 |
| 5 | 2.356 | 1.791 |
| 6 | 2.500 | 1.851 |
| 7 | 3.355 | 2.352 |
| 8 | 3.451 | 2.307 |
| 9 | 2.288 | 1.790 |

- All timing rows are truncated by the existing text logger. Missing Turn-3 LLM nodes remain
  unavailable; no LLM-generation timing credit is inferred. Last Turn was aborted/closed, so
  first-audio timing does not prove complete audio drain. Human speech-end/acoustic output and
  interrupt-to-silence latency remain unmeasured. No input replay or optimization occurred.
- USER clarified the exact final sequence: short-press to standby, then long-press to stop App.
  This is supported operation, not operator misuse. Short-press speak convergence hit the
  Level-1 timeout; the later long-press shutdown hit TTS stop-state rejection.
- Source inspection: `MatchaTTSAdapter.stop` forces a BUSY child to DESTROYED, but another stop
  then delegates DESTROYED to `FramedProcess.stop`, which permits only READY/STOPPED. `Speak.stop`
  also stops its TTS adapter, and Resource Manager separately stops that backend. Thus repeated
  shutdown after a forced termination has an unsafe stop-state boundary. Exact live child state
  and abort escalation were not captured, so this is a localized failure mechanism to reproduce,
  not a claim that the full live causal sequence is already proven.
- Next bounded diagnosis: reproduce the confirmed short-press/standby/long-press sequence and
  the TTS abort/stop state boundary. This is a real interrupt/shutdown failure risk, not an administrative gate.
  No fix or new test matrix was implemented during this read-only observation/recording step.

### Fixed offline installation work package — 2026-10-09

- USER rejected the temporary-checkout command as formal delivery and instructed completing
  startup before wrapping it as a service. Proceed without another proposal-only pause.
- Value/risk: formal startup must not depend on development/checkpoint config, model, locks,
  controller/LLM venv or Display library. Existing accepted audio products under
  `/var/lib/snowboard/products/` remain stable shared dependencies, not duplicated research.
- Estimate: 3 points. Affected paths: `scripts/install_app.py`, `tests/test_app_install.py`,
  existing launcher/tests as necessary and this status. Install a fresh fixed product directory;
  reject existing destinations rather than overwrite. Copy tested source, runtime, model, locks,
  release profile and Display library; rewrite only deployment paths plus private log location.
  No service, startup digest, source optimization or voice-question change.
- Installed fixed directory: `/home/<operator>/snowboard-app`, initially confirmed not present. Entry is
  `<prefix>/run.sh`, defaults select that installation's Python/config without command arguments.
  Use installed stable ASR/TTS audio product dependencies. Preserve previous source and evidence.
- Workstation final installer/launcher tests: **14 Pass**, exit 0. Pi final installation/launcher
  and ALPHA driver/oracle/runner tests: **74 Pass**, exit 0, 1.09 s;
  `/home/<operator>/alpha-launcher-20261009-x1EXAr/install-final-regression-02.log`.
- Installation diagnosis preserved: initial model copy used a generic basename, corrected before
  first native startup to preserve the locked model filename. First native installed launch then
  exited **4**, missing the audio runtime-lock companion because lock files had been relocated
  outside `requirements`. Final installer preserves `requirements/m4a` companions and the
  `requirements/m4b` layout needed by LLM factory root inference. Tests now assert those paths.
  Initial failed terminal log is `<verification-root>/installed-startup-01.log`; the CRITICAL row
  remains in the installed product log. Do not relabel it as a successful launch.
- Operator corrected only the newly created installation's model name and lock/config paths to
  match the final installer output, retaining old evidence and source. Final config parses and
  product composition initializes successfully. No product source/API/prompt or admission changed.
- Final installed entry was run twice from `/tmp` with **no arguments**. Both reached clean IDLE;
  terminal Ctrl+C returned **exit 0**, with no installed App/LLM/ASR process and no capture,
  playback, SPI or GPIO holders after each shutdown. Private terminal records:
  `<verification-root>/installed-startup-02.log`, `installed-startup-03.log`, where
  `<verification-root>` is `/home/<operator>/alpha-launcher-20261009-x1EXAr`.
  First corrected model startup took roughly a minute; next startup succeeded much faster.
  This is a deployment observation, not controlled before/after performance or a proven cause.
- Installed controller/LLM Python, model, release profile, artifact locks and Display library now
  live under the product prefix; ASR/TTS use the existing `/var/lib/snowboard/products` deployment.
  Old editable-package hooks were omitted from the copied runtime. No application runtime path
  depends on ALPHA test directories. Model/runtime preparation is offline and leaves sources intact.
- Independent transfer-boundary dry-run comparisons found no differences for four installer/
  launcher/test files on Pi and for installed `src`, `requirements`, launcher (cache excluded).
  Workstation/Pi compile, shell syntax, whitespace and changed-file privacy checks Pass.
  App was stopped after verification; Pi remains online. No service, commit/push or final
  whole-ALPHA acceptance is claimed. Installation-specific voice use remains available to USER.

#### Fixed installed operation — current entry

On the Pi, from any directory:

```bash
~/snowboard-app/run.sh
```

- Wait for the Display to show standby, then short-press to start speaking. Short-press during a
  Session ends it; long-press or terminal Ctrl+C stops App, not Pi. Keep the terminal open.
- Logs: `~/snowboard-app/logs/application.log` (private, current text-log truncation still applies).
  Use `tail -f ~/snowboard-app/logs/application.log` in a second terminal for state/error monitoring.
  `~/snowboard-app/run.sh --help` explains the launcher. No venv activation, Python/config arguments
  or knowledge of candidate/test paths is needed for normal operation.
- Installer for a future fresh prefix is `scripts/install_app.py --prefix <new-product-directory>
  --python <tested-controller-venv>/bin/python --config <tested-product-config>`. It rejects existing
  destinations; it is not an updater. Any later service must call this same installed `run.sh`,
  not introduce a second product startup path or modify this WIP's history.

### Terminal launcher work package — 2026-10-09

- USER approved completing a terminal launcher before ALPHA delivery. Value/risk: USER must be
  able to run/stop the real App independently, with the intended config and repository code;
  missing config must not silently start a mock default. No systemd/service or auto-start change.
- Estimate: 2 points. Affected paths: `scripts/run-app.sh`, `tests/test_app_launcher.py`, this
  existing operator/status document. Scope: ALPHA external launcher startup/shutdown and live
  microphone entry; existing product composition, prompt, timings and input behavior stay unchanged.
- Implemented: foreground shell `exec` of the existing production `run_app`, explicit `--config` and
  `--python` with repository-local defaults, help/argument checks, Ctrl+C graceful shutdown.
  No background daemon, PCM injection, automatic digest check or new acceptance gate.
- Workstation: **9 launcher tests Pass**, exit 0. Pi: **69 launcher/ALPHA driver/oracle/runner
  tests Pass**, exit 0, 1.37 s. Tests execute the shell/subprocess path, check default and relative
  paths (including spaces), repository import precedence, missing config/Python errors, actual
  exit-code propagation and SIGINT delivery across shell `exec`. Native proof is separate below.
- New isolated Pi checkout: `/home/<operator>/alpha-launcher-20261009-x1EXAr/repo`, WIP `9c13509`
  from standard Git bundle plus the two new files. Portable log: `<root>/launcher-regression.log`.
  Same existing production Python and unchanged v3 config/profile were used; older candidates
  and live-test evidence were preserved.
- Twice ran the executable script on a real Pi terminal with production hardware to clean IDLE,
  then sent terminal Ctrl+C. Both App exits were **0** (retained by `script -e`), with no matching
  App/LLM/ASR process and no capture/playback/SPI/GPIO hardware holder after each shutdown.
  Logs are private `<root>/startup-01.log` and `startup-02.log`; no voice input was injected.
  This verifies launcher startup/stop/restart, not a repeat of the full ALPHA Lifecycle run.
- Workstation/Pi shell syntax, compile and whitespace checks Pass. One independent transfer-boundary
  `rsync -nrcRi` comparison found no byte differences for the launcher/test files. Privacy checks
  cover only the public changed files; raw terminal logs remain on Pi. App was stopped after both
  checks; Pi remains online. No commit/push or formal final ALPHA Verify is claimed.

#### Development-only predecessor — superseded by fixed installed operation above

- With `.venv/bin/python` and `config.local.yaml` installed in the repository, run
  `./scripts/run-app.sh`. Otherwise supply `--python` and `--config` explicitly. Defaults are
  relative to the script's repository, while supplied relative paths are relative to your terminal.
- Retained development checkout/config: replace the operator placeholder with your Pi account in this example.

```bash
cd /home/<operator>/alpha-launcher-20261009-x1EXAr/repo
./scripts/run-app.sh \
  --python /home/<operator>/snowboard-agent-dev/core/.venv/bin/python \
  --config /home/<operator>/alpha-performance-v3-20261003-qFdPG1/product.local.yaml
```

- Wait for `M2 runtime ready state=IDLE`, short-press to begin a live microphone conversation;
  short-press again to stop that conversation. Long-press or Ctrl+C exits App normally, not Pi.
  The script stays in the foreground; closing the terminal may stop App. It is not a service,
  background launcher or login-independent daemon. `./scripts/run-app.sh --help` requires no
  config/native runtime and explains these controls.
- For SSH operation, open an interactive terminal with `ssh -t <operator>@<pi-host>` first and
  keep it open while using the App. Do not use the discarded ephemeral agent SSH launch method.

### Live microphone session resumed — 2026-10-09

- USER resumed from WIP `9c13509`, confirmed Pi availability and requested live microphone testing.
  USER considers the previous Quality findings tolerable and explicitly instructed not to reuse
  those questions. Do not replay the old six-case script or pursue those defects as today's task.
  Existing strict test cards remain unchanged; live conversation is separate development evidence.
- Pi capture/playback Voice HAT devices are present and no product App was running. One independent
  transfer-boundary comparison found no differences in the eight modified code/test/profile files
  between the WIP and the existing v4 checkout. Production config selects ALSA, whispercpp,
  litert_lm, sherpa_matcha, enabled physical Button and ssd1351 Display.
- Planned launch: from `<v4-root>/repo`, set `PYTHONPATH=src` and use the existing product Python
  to call `asyncio.run(sbd.main.run_app(<v3-root>/product.local.yaml))` directly. No fixed PCM,
  injected Button, fault injection, ASR rewrite or backend substitution. User speaks freely and
  reports the observed microphone, speaker, Display and multi-turn behavior. Production startup
  reached `M2 runtime ready state=IDLE` at 16:22:38 +08:00 on 2026-10-09; live USER observations
  and final App shutdown remain pending. The first interactive SSH process did not persist:
  later inspection found no product App, and USER reported no button response with the last
  standby frame retained on Display. That startup is not a completed live test.
- Relaunched the same production entrypoint with `nohup`, stdin detached, and private mode-0600
  stdout/stderr log at `/home/<operator>/alpha-live-20261009-VkWLZT/application.log`.
  This changes operator launch supervision only, not product source/config. Recorded App PID
  is 1313; confirm its current identity before any later signal. Relaunch reached clean IDLE
  at 16:25:47 +08:00. Live monitoring then observed WAKE → PERCEPTION → THINK → ACTION →
  PERCEPTION, followed by the next THINK. Button-triggered real input and a return to listening
  are observed; audible output/answer quality still require USER confirmation. This is not a
  semantic PASS inferred from state transitions. The App remains running for USER testing.
- USER reported completion of the live test and a physical button press returning the Display
  to standby. Log confirms one Button-started Session with four THINK → ACTION → PERCEPTION
  cycles, then PERCEPTION → IDLE at 16:27:25 +08:00. App PID 1313 remained running afterward.
  No ERROR/WARNING appeared in the inspected recent log window. The operator/button/standby
  observations are recorded. USER subsequently confirmed "功能皆正常" after discussion of
  live input/output, pauses, interruption and spoken end/restart. Record the live functional
  experience as USER-confirmed normal; no per-scenario timings, exhaustive factual correctness
  or measured environmental-noise robustness is inferred from that overall confirmation.
  App is intentionally left in IDLE; USER has not requested App stop or Pi shutdown this session.
- USER later reported closing the App. Follow-up SSH inspection confirmed PID 1313 was absent
  and no matching `run_app`, `sbd.main`, LiteRT LLM worker or whisper server process remained.
  Pi itself remained reachable. Last logged transitions at 16:32:45–16:32:49 +08:00 were
  IDLE → WAKE → PERCEPTION → IDLE. Detached launch did not retain an exit-status file, so
  process absence is confirmed but exit code 0 is not independently claimed.
- Live functional testing is complete to USER's satisfaction. Remaining work is synchronization
  of tested prompt/fixture and USER-directed Quality scope into existing authority/Test Spec,
  followed by applicable final common-candidate Pi Verify/content reconciliation. Do not replay
  retired quality questions or add further live cases without a concrete risk or USER request.
  Original quality FAIL cards remain intact; this confirmation does not by itself complete the
  outstanding formal Verify. Before the subsequent launcher work, only Developer status changed.
- USER asked whether response times were recorded. The retained live log has four timing and four
  runtime rows and zero ERROR/WARNING rows. Existing log sanitization in `src/sbd/core/logger.py`
  truncates messages to 512 characters; every timing row is truncated. Only ASR final, first audio
  write, Conversation ready, first safe text and LLM send nodes survive completely. No raw spoken
  transcript is captured by this launch. The following intervals were reconstructed directly from
  surviving controller-monotonic timestamps without replaying input:

| Live Turn | ASR final → first audio write (s) | LLM send → first safe text (s) | Safe text → first audio write (s) |
| :--- | ---: | ---: | ---: |
| 1 | 13.668 | 12.971 | 0.519 |
| 2 | 2.756 | 2.067 | 0.514 |
| 3 | 3.036 | 2.279 | 0.581 |
| 4 | 3.226 | 2.277 | 0.773 |

- ASR final → LLM send was 0.178 / 0.176 / 0.177 / 0.176 s. First-Turn generation latency is
  visibly larger; its cause is not established. Do not claim warm-up or an optimization benefit.
  These intervals begin after ASR completion and end at an audio write, not at human speech end
  or acoustic sound perception. PERCEPTION duration also includes listening/pauses and cannot
  substitute for ASR processing latency. Physical button time, exact speech end, LLM terminal,
  full TTS/Audio drain and interrupt-to-silence latency cannot be reconstructed precisely here.
  If complete live timing is needed next, retain structured boolean/count/timing-only observations
  outside the truncated text logger; do not disable privacy sanitization or claim this run contains
  missing nodes. No code change or additional live run was made for this timing inspection.
- Existing CLI `python -m sbd.main` reads `config.local.yaml` from its working directory; it has
  no config argument or dedicated ALPHA one-command wrapper. Today's direct API launch uses the
  existing explicit config without changing source or overwriting the candidate.
- Prompt correction is already implemented in WIP: `明確要求對話結束時`, metadata 59/9/68.
  Remaining prompt feedback is synchronization of the existing authority/Test Spec with tested
  bytes, not a new prompt experiment or prerequisite document approval. No additional wording
  change is planned before this live test.

### USER-requested pause and next-session entry — 2026-10-03

- USER subsequently requested a WIP commit of these ten changed files, approved the displayed
  subject/body/file list, and directed future work to continue from that WIP snapshot. This is an
  explicit incomplete-Verify preservation exception, not formal acceptance or permission to push.
  Future changes are appended in new commits; do not amend or rewrite this WIP. Published record
  locators use operator/host placeholders; run IDs and evidence directory names remain unchanged.
- USER requested stopping here, completing the record and shutting down `<operator>@<pi-host>`.
  Do not continue tests, diagnosis or implementation until USER resumes. Shutdown command
  `ssh <operator>@<pi-host> 'sudo -n systemctl poweroff'` completed with exit 0; one subsequent
  SSH check exited 255 because `<pi-host>` no longer resolved via mDNS. This confirms the
  shutdown request was accepted and SSH was unavailable; physical power state was not inspected.
- Development results: Lifecycle v2 PASS; Performance v3 VALID_BASELINE with no optimization adopted;
  Recovery v4 PASS; Quality v4 objective six/six PASS and semantic four/six PASS, two FAIL.
  Exact candidate roots, commands, regressions and retained evidence are recorded below.
- After reading the actual Quality transcript, USER considered the overall experience acceptable,
  with no severe off-topic behavior or rule violation. Preserve this product assessment separately
  from the strict test card: Q05 geographic factual error and Q06 ASR arithmetic-intent corruption
  remain improvement findings, not evidence that dialogue lifecycle/keep/end rules failed.
  No existing FAIL card is rewritten and no formal ALPHA acceptance is inferred.
- All current voice tests used fixed synthesized PCM through `AudioInput.frames`, not microphone
  acoustic capture. Suggested next practical check is USER-assisted live microphone input, noise
  and pauses; its scope is to be agreed on resume, not an added mandatory ALPHA gate.
- Remaining next-session work: decide the two Quality findings' disposition/targeted diagnosis;
  feed measured prompt and fixture revisions back to existing design/Test Spec; finish applicable
  final Pi Verify against one common final candidate/input mapping, reconcile workstation content,
  then request explicit approval of any commit proposal. Do not splice v2/v3/v4 development runs
  into a final common-candidate acceptance result.
- Resume pointers: Developer-owned status is this file; latest deployed code is
  `/home/<operator>/alpha-recovery-v4-20261003-qJ7Sbh/repo`; retained config and fixed PCM are under
  `/home/<operator>/alpha-performance-v3-20261003-qFdPG1/` as specified below. Next owner is Developer
  after USER resumes. `docs/status/current.md` was not changed.
- Changes were uncommitted when USER paused testing; the subsequent WIP snapshot is authorized
  above. No push or new handoff document was requested. Existing Pi candidate directories and
  private evidence are retained, not deleted.

### Authority, value and scope

- Developer entry is Open in `docs/status/current.md`; authority is `docs/milestones/ALPHA.md`
  §§3–8 and `docs/test_spec/test_spec_ALPHA.md` §§3–7.
- Implement only the runner gaps for the four independent runs. Retain observations that identify
  stale work/owners, missing timing, failed recovery or unusable speech. No optimization is planned
  before a valid Pi baseline identifies a concrete bottleneck.
- Existing user changes to current status, the ALPHA Test Spec and its completed review are preserved.

### Work package estimate and planned affected paths

| Package | Estimate | Paths | Test IDs / verification |
| :--- | :--- | :--- | :--- |
| Production launcher driver and fixed PCM binding | 5 points | `scripts/alpha_product.py`, `tests/test_alpha_product.py` | All four ALPHA runs; real App supervision, production ASR/LLM/TTS/Audio, ordered Session fixtures |
| Timeout runner, public evidence and path oracles | 5 points | `scripts/run-alpha-pv.py`, `scripts/alpha_oracle.py`, `tests/test_alpha_pv_runner.py` | Lifecycle, Performance, Recovery and Quality; first failure, bounded cleanup, privacy-safe evidence |
| Run-specific observation and portable integration | 5 points | Above driver/tests; `src/` only if an actual product gap is demonstrated | Three Session barriers, P01–P05 causal timing, child kill/replacement, six once-only quality cases |

- Planned workstation verification: `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/test_alpha_product.py tests/test_alpha_pv_runner.py`; directly affected M4C/Reasoner tests;
  `PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not rpi'`; `git diff --check`.
- Planned Pi interface: `.venv/bin/python scripts/run-alpha-pv.py --run
  {lifecycle,performance,recovery,quality}` with explicit config, fixed fixture mapping, private/public
  output roots and finite watchdog. The interface is implemented; Pi results remain pending.
- USER confirmed on 2026-10-02 to follow the corrected documents: keep existing admission behavior,
  one Button per Session and the shorter fixed stimuli. Implement the runner without product API changes.
- USER subsequently explicitly requested commit/push after workstation testing, with Pi testing on
  the new workstation. This delivery overrides the usual pre-commit Pi order for this work package
  only; it is not Pi Verify, formal acceptance, or permission to amend a pushed candidate.

### Implementation result — 2026-10-02

- `scripts/run-alpha-pv.py` exposes exactly four independent runs, a finite invocation watchdog,
  first-failure retention, bounded cleanup of observed native child groups and sanitized evidence.
  Output directories are fresh and outside the repository; private answers/audio stay mode 0600.
- `scripts/alpha_product.py` invokes the existing `sbd.main.run_app` with its default production
  composition, validator, supervision and shutdown. Observation wrappers preserve existing calls;
  fixed PCM enters `AudioInput.frames`, while Button stimuli use the production GPIO button callback.
  ASR, LLM, TTS and Audio output execute normally; R1 input-limit speech cannot earn LLM path credit.
- Lifecycle executes three two-turn Sessions, observes each cleanup barrier, shuts down and restarts
  the launcher. A network namespace disables external networking; strace records network syscalls
  across both processes. One aggregate scan inspects the sanitized public report and actual emitted
  console/file logs from both launches, including Unicode JSON output and private credential matching
  in memory. Only aggregate counts are retained; short numeric answers do not match case-ID substrings.
- Performance records P01–P05 separately, including controller-clock startup/resource readiness,
  existing LLM timing, actual TTS batches/PCM/audio segments and token counts. It validates concurrent
  causal branches and retains invalid samples. Controlled PCM speech end is the last non-silent frame
  delivered to ASR. No optimization or numerical latency threshold is introduced before the Pi baseline.
- Recovery terminates the actual sole LLM child after safe-fragment admission, observes failure and
  barrier rejection, one replacement, a new complete Session and final release of product owners.
- Quality executes the six fixed cases once. Q05 closes through the existing short-press interruption
  after both voice turns complete; no third PCM or ASR terminal is admitted. A pending semantic card
  returns non-zero. Codex subsequently adjudicates the same private observation without another run;
  objective failure cannot be overridden. Public reasons are stable codes, never response excerpts.
- `IR_dev_ALPHA_I` is Resolved at `docs/reviews/history/IR_dev_ALPHA_I.md`; the corrected Button and
  fixture contracts are implemented. No product source or admission behavior was changed.

### Workstation verification

- Focused ALPHA and directly affected M4C/Reasoner command: **125 selected tests Pass**, exit 0.
- Final ALPHA driver/oracle/runner tests include actual Listen → Reasoner → StreamingSpeak → Audio
  controller integration for repeated Sessions and quality scheduling, actual subprocess watchdog and
  separate child-group cleanup, immutable PCM binding, concurrent timing, public privacy and same-run
  semantic adjudication. Latest affected-test result: **130 selected tests Pass**, exit 0.
- Earlier complete non-RPi runs: **1943 Pass** before the final additions, then **1940 Pass / 5 Fail**;
  failures were existing 3-second acceptance, 90-second nested suite, and 5-second child/App startup
  watchdogs. The exact five-test rerun retained three timeouts; a subsequent unchanged-limit rerun
  of those three passed (**3/3**, 30.48 s). Failure records are not relabeled as passing.
- Final complete non-RPi regression on the latest implementation:
  `PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not rpi' -o addopts=''`:
  **1948 Pass**, **35 deselected Pi tests**, exit 0, 220.29 s; zero Fail/Skip/XFail.
- `PYTHONPATH=src .venv/bin/python -m compileall -q src scripts tests`: Pass.
- Staged source/test whitespace checks and `scripts/privacy_gate.py scan-staged`: Pass.
  Markdown checks preserve the pre-existing intentional CommonMark hard break in `TR_spec_ALPHA_I`;
  that resolved review is not rewritten for whitespace-only cleanup.
- Actual workstation CLI invocation returns exit 2 with `INVALID / PI_TARGET_REQUIRED`; it cannot
  produce a Pi Pass on the x86_64 workstation.

### Pi execution interface and next action

Use the deployed production voice-only config with the existing M4 native runtime/model paths. Prepare
the fixed local PCM once before all four runs (or provide an already fixed recorded PCM mapping):

```bash
timeout 300s .venv/bin/python scripts/alpha_product.py \
  --config /path/to/product.local.yaml --prepare-fixtures /tmp/alpha-fixed-pcm
```

The preparation uses the offline production Matcha TTS, produces 16 kHz mono S16_LE WAV files plus
`fixtures.json`, and shares identical-question bindings. These are inputs, not acceptance observations.
Do not replace fixtures after the first valid run stimulus; all four runs use this same mapping.

```bash
.venv/bin/python scripts/run-alpha-pv.py --run lifecycle --run-id ALPHA-L01-DEV-01 \
  --config /path/to/product.local.yaml --fixtures /tmp/alpha-fixed-pcm/fixtures.json \
  --output /tmp/alpha-l01-dev-01 --watchdog 900 --network-launcher sudo-unshare
```

`sudo-unshare` uses noninteractive sudo to create the network namespace, then `setpriv` returns to
the invoking user's UID/GID/groups before strace and App execution; private artifacts remain readable
by that user. If the invoking account can
create a network namespace directly, use the default `--network-launcher unshare`. Missing privilege
or strace makes the run non-passing; it does not disable offline observation. Both child launches use
the same invocation watchdog. Every output directory must be new.

Performance, Recovery and Quality use the same command with `--run performance|recovery|quality`,
their own run ID and new output directory; they do not repeat lifecycle/network/privacy observations.
For Quality, Codex privately inspects `private/run-observation.json` on the Pi and supplies a local
JSON object keyed by the six case IDs, each with `disposition` and a sanitized `reason_code`. Finalize
that same run without executing product input again:

```bash
.venv/bin/python scripts/run-alpha-pv.py --run quality \
  --adjudicate /tmp/alpha-q-dev-01 --judgments /path/to/private/semantic-judgments.json
```

- Workstation development/testing completed on 2026-10-02. Pi development execution on 2026-10-03
  exposed the runner and product-path failures below. Next owner remains Developer; final Pi Verify
  is pending convergence.
- No ALPHA acceptance is claimed. Delivery follows USER's explicit pre-Pi commit/push
  instruction with approval of the complete message/file list; `current.md` remains Designer-owned.

### Quality result — 2026-10-03

- USER selected Quality. No code, prompt, questions or PCM were changed. Ran each Q01–Q06 once
  on `/home/<operator>/alpha-recovery-v4-20261003-qJ7Sbh/repo` using the fixed v3 input mapping/config.
- Command: `/home/<operator>/snowboard-agent-dev/core/.venv/bin/python scripts/run-alpha-pv.py
  --run quality --run-id ALPHA-Q-DEV-20261003-02
  --config /home/<operator>/alpha-performance-v3-20261003-qFdPG1/product.local.yaml
  --fixtures /home/<operator>/alpha-performance-v3-20261003-qFdPG1/fixed-pcm/fixtures.json
  --output /home/<operator>/alpha-recovery-v4-20261003-qJ7Sbh/quality-02 --watchdog 900`.
- All six objective cases passed, including all twelve case/cleanup Turns, six Session barriers,
  expected keep/end routes and final process/ALSA/display/hardware-owner absence. Initial exit 2
  was `NEEDS_USER_DECISION / SEMANTIC_OBSERVATION_PENDING`, the runner's unjudged semantic card,
  not a request for USER to judge already-defined factual criteria.
- Codex inspected the same private ASR, responses and delivered fragment text. Semantic results:
  Q01 identity PASS; Q02 seven-day fact PASS; Q03 no-vision honesty PASS; Q04 one-sentence helmet
  head-safety relevance PASS; Q05 context FAIL (`LOCATION_FACTUAL_ERROR`); Q06 arithmetic/end
  FAIL (`ARITHMETIC_INTENT_LOST_IN_ASR`). Q05 resolved the pronoun and stayed location-focused
  but gave an incorrect relative location. Q06 ASR changed the arithmetic intent to an E-related
  request, so the spoken result failed the original question; keep/end routing itself was correct.
  Q04 also had ASR word deviations, but its delivered answer still met the semantic criterion.
- Same-run adjudication uses `scripts/run-alpha-pv.py --run quality --adjudicate <root>/quality-02
  --judgments <root>/quality-02/private/operator-judgments.json`; no questions were replayed,
  selected, corrected in transit or replaced. Final **FAIL**, exit 2, `SEMANTIC_FAILED`.
  Public card: `<root>/quality-02/adjudicated-result.json`; original card remains `result.json`;
  private observation and judgment files remain under `private/`. No unresolved preference or
  `NEEDS_USER_DECISION` remains after this adjudication.
- Value/risk for the next bounded diagnosis: ASR intent corruption produces an unrelated answer;
  geographic factual error makes otherwise coherent conversation unreliable. Inspect ASR first
  using matched diagnostics without treating retries as acceptance; then localize Q05's model
  factual issue. No new code work item or numerical gate is introduced in this run.
- USER subsequently paused work; the next-session routing/product assessment is recorded at the top.
  Quality convergence and final common-candidate
  Pi Verify remain incomplete; no ALPHA acceptance, commit or push is claimed.

### Recovery repair result — 2026-10-03

- USER selected Recovery. `ALPHA-R01-DEV-20261003-02` on the v3 candidate failed only
  `old_reaped`; replacement count was one, barrier rejection and failed-work cleanup succeeded,
  and the replacement completed both normal Turns. Final owner absence was true.
- Diagnostic: production child cleanup awaits the process and then clears `_process`; the runner
  incorrectly reads that cleared reference after recovery. Preserve the actual subprocess handle
  at fault injection and require its exit code plus PID absence. Do not relax the oracle.
- Value/risk: distinguish a reaped real process from missing observation; retain the original failed
  run. Estimate: 1 point. Affected paths: `scripts/alpha_product.py`, `tests/test_alpha_product.py`,
  this status. Test ID: `ALPHA-R01-LLM-RECOVERY`.
- Implemented: retain the actual subprocess handle at injection and inspect its return code plus
  PID absence after recovery. Production lifecycle, fault handling and acceptance oracle are unchanged.
  Added a real subprocess regression covering live process, waitpid, cleared child reference and
  rejection when PID absence cannot be established.
- New isolated candidate: `/home/<operator>/alpha-recovery-v4-20261003-qJ7Sbh/repo` with the current eight
  modified code/test/profile files over baseline `bb5951e`. The command deliberately reuses the
  unchanged v3 config, revised release profile and fixed PCM; no input was regenerated or replaced.
- Command from the new checkout: `/home/<operator>/snowboard-agent-dev/core/.venv/bin/python
  scripts/run-alpha-pv.py --run recovery --run-id ALPHA-R01-DEV-20261003-03
  --config /home/<operator>/alpha-performance-v3-20261003-qFdPG1/product.local.yaml
  --fixtures /home/<operator>/alpha-performance-v3-20261003-qFdPG1/fixed-pcm/fixtures.json
  --output /home/<operator>/alpha-recovery-v4-20261003-qJ7Sbh/recovery-03 --watchdog 900`.
- **PASS**, exit 0: actual sole LLM child killed after one safe fragment; one expected backend fault;
  old child reaped; no future fragments or normal failed-turn terminals; failed work empty; error
  display clear; barrier admission rejected; exactly one READY replacement; new empty Conversation
  completed the normal and close Turns; final process/ALSA/display/hardware-owner absence all true.
  The injected Turn's failed path is expected and is not relabeled as a successful normal Turn.
- Public evidence: `<root>/recovery-03/result.json`; private observations/logs remain under
  `<root>/recovery-03/private/`. Original v3 failure is preserved under
  `/home/<operator>/alpha-performance-v3-20261003-qFdPG1/recovery-02/`.
- Workstation affected driver tests: **15 Pass**, exit 0. Pi ALPHA driver/oracle/runner regression:
  **60 Pass**, exit 0, 0.85 s; `<root>/alpha-regression.log`. Workstation/Pi compile and whitespace
  checks Pass. One independent transfer-boundary `rsync -nrcRi` comparison found no differences
  across the eight modified code/test/profile files; no recurring digest assertion was added.
- Recovery is a development Pass; subsequent Quality results are recorded above. It is not formal ALPHA acceptance;
  full final common-candidate Pi Verify remains pending. No commit/push was performed.

### Performance baseline result — 2026-10-03

- USER selected Performance after Lifecycle. Test ID: `ALPHA-P01-PERFORMANCE`; no numerical
  threshold, concurrent workload, source optimization or repeated fault/privacy/lifecycle matrix.
- First measurement on the v2 candidate, `ALPHA-P01-DEV-20261003-02`, was **INVALID**, exit 2,
  `MULTIPLE_FRAGMENTS_MISSING`. All six real ASR/LLM/Audio Turns and both Session barriers completed;
  all final owner-cleanup booleans were true. P01–P04 samples remain available, but P05 produced one
  short fragment. Its actual ASR had a word deviation and the model returned one short sentence.
  Public result and private observations remain under
  `/home/<operator>/alpha-lifecycle-v2-20261003-IUveqU/performance-02/`; no sample was dropped or relabeled.
- Value/risk and repair: P05 must exercise actual multi-fragment scheduling to expose TTS/Audio timing.
  Estimate: 1 point. Only `scripts/alpha_product.py` fixture text and this status were changed.
  USER previously authorized empirical question reselection without a preceding document gate.
  Selected `FX-MULTI-FRAGMENT`: 「請列出三個滑雪安全重點。」. Prompt, product API, model/runtime,
  admission thresholds, fragment boundaries, timing instrumentation and other input bindings are unchanged.
- One native two-turn diagnostic in the matched weekday context produced three natural fragments,
  `end=false`. Private log:
  `/home/<operator>/alpha-lifecycle-v2-20261003-IUveqU/performance-stimulus-debug-01.log`.
  Native-only diagnosis does not earn Performance acceptance credit.
- New isolated candidate root: `/home/<operator>/alpha-performance-v3-20261003-qFdPG1`; code under `repo/`,
  config `product.local.yaml`, same revised release profile. Prepared only the replacement PCM;
  all other PCM files and the mapping were copied byte-for-byte from v2 before first stimulus.
  New mapping: `<root>/fixed-pcm/fixtures.json`. Earlier candidate inputs/evidence are preserved.
- Run command from `<root>/repo`: `/home/<operator>/snowboard-agent-dev/core/.venv/bin/python
  scripts/run-alpha-pv.py --run performance --run-id ALPHA-P01-DEV-20261003-03
  --config <root>/product.local.yaml --fixtures <root>/fixed-pcm/fixtures.json
  --output <root>/performance-03 --watchdog 900`.
- **VALID_BASELINE**, exit 0. All P01–P05 required nodes and causal orders completed. P02/P03 used
  the identical matched PCM and reused the engine/child; both close Turns completed but are excluded
  from numeric case values. P05 admitted three fragments, synthesized as two actual TTS batches.
  Final product process/hardware-owner cleanup is true.
  Public nodes/result: `<root>/performance-03/result.json`; actual logs/observations stay private
  under `<root>/performance-03/private/`.

| Case | Measured interval | Seconds | Largest directly measured stage |
| :--- | :--- | ---: | :--- |
| P01 startup | Process start → clean IDLE | 4.496 | Config complete → IDLE, 4.247 s |
| P02 first Turn | Conversation ready → Audio complete | 9.312 | PCM speech end → ASR final, 3.777 s |
| P04 follow-up | Previous Audio complete → current Audio complete | 7.428 | Next perception start → ASR final, 3.875 s |
| P03 warm Session | New Conversation ready → Audio complete | 9.058 | PCM speech end → ASR final, 3.729 s |
| P05 streaming | LLM send → final audio drain | 6.830 | LLM send → terminal, 3.760 s |

- P02/P03 controlled PCM speech-end → first positive audio write: 7.231 / 6.982 s.
  LLM send → first safe text: 2.353 / 2.219 s. First safe text → first TTS PCM: 0.924 / 0.860 s.
  P05 per-fragment queue wait: 0.044 / 1.112 / 0.596 s; later fragments share a real TTS batch.
  The intervals have different endpoints and overlap; do not sum generation/audio branch durations.
  Fixed PCM is delivered through the real ASR seam, not live microphone capture or real-time human speech.
- ASR finalization is the largest measured pre-response phase in the matched short-input cases.
  This identifies where time is spent, not an avoidable code defect, nor evidence of stable warm-session
  improvement. No bounded optimization item was opened or optimization benefit claimed.
- Workstation affected driver tests: **14 Pass**, exit 0. Pi ALPHA driver/oracle/runner tests:
  **59 Pass**, exit 0; `<root>/alpha-regression.log`. Workstation/Pi compile and whitespace checks Pass.
  One independent transfer-boundary `rsync -nrcRi` comparison found no content differences for the
  eight modified source/test/profile files. No recurring digest assertion was added.
- Measured feedback: synchronize the Performance/Recovery shared multi-fragment fixture wording in
  ALPHA/Test Spec after experimentation. Its binding is fixed for subsequent v3 runs.
  Lifecycle v2 remains a separate recorded development Pass; final ALPHA evidence cannot splice
  candidates and must use the final common content/fixtures. Do not rerun unchanged development
  Lifecycle solely for this preparation-only text change.
- Performance baseline is complete. Recovery subsequently passed on v4 with the retained-process
  observation repair above. Quality subsequently failed semantic criteria; full common-candidate Pi Verify remains pending.

### Lifecycle repair result — 2026-10-03

- USER selected Lifecycle first, authorized changing the prompt and reselecting its LLM question,
  and instructed us to feed empirical results back afterward instead of waiting for Designer
  document changes. This supersedes the earlier fixed-prompt blocker for this bounded repair.
- Implemented prompt clause: `明確要求對話結束時`. Core/personality/combined tokens: 59/9/68.
  Updated prompt/dashboard/profile metadata consistently; retained the deployed profile family ID,
  model/runtime/schema, admission limits and product API. Startup prompt composition now compares
  actual strings without calculating a text digest. Existing metadata was updated once at the
  candidate-change boundary; no new recurring checksum test or administrative gate was added.
- Reselected `FX-SHORT-A` to 「一個星期有幾天？」. Its synthesized PCM reaches actual ASR, and the
  resulting text reaches LLM unchanged, including punctuation. `FX-NORMAL-END` remains 「現在請結束對話。」.
  No model route is forced. Fixed PCM bypasses acoustic microphone capture via `AudioInput.frames`;
  downstream production ASR, LLM, TTS and ALSA output execute normally. This is not live-microphone
  or environmental-noise coverage.
- Runner Session observation now obtains the actual Session identity from a durable PCM row,
  avoiding a hang when a complete two-turn Session finishes between polls of the live pointer.
  The actual-controller regression includes precisely that Lifecycle ordering.
- Value/risk and scope: fix unintended dialogue termination and missed Session observations.
  Estimate: 2 points for observer repair plus 3 for prompt/question convergence.
  Affected paths: `scripts/alpha_product.py`, `src/sbd/cognition/{prompt_builder,observability}.py`,
  `requirements/m4b/{product-profile,llm-artifacts}.json`, their direct tests and Developer-owned
  status/review. Test ID: `ALPHA-L01-LIFECYCLE`. Quality conditional-close repair remains deferred.

#### Pi candidate and Lifecycle evidence

- Target: `<operator>@<pi-host>`, aarch64. Base `bb5951e` plus the eight modified source/test/profile
  files, isolated root `/home/<operator>/alpha-lifecycle-v2-20261003-IUveqU`; code is under `repo/`.
  Existing deployments, earlier fixtures and failed evidence were preserved.
- Product Python: `/home/<operator>/snowboard-agent-dev/core/.venv/bin/python`, 3.13.5.
  Candidate config/profile: `<root>/m4c-product-config.yaml`, `<root>/m4err-release-profile.json`.
  Existing release memory thresholds and native/model paths are unchanged. Candidate config points
  to the candidate's revised LLM lock/profile.
- Prepared fixed PCM once with `timeout 300s <product-python> scripts/alpha_product.py
  --config <root>/m4c-product-config.yaml --prepare-fixtures <root>/fixed-pcm`: 13 fixture IDs.
  The mapping is `<root>/fixed-pcm/fixtures.json` and remains fixed for this candidate's later runs.
- Lifecycle command from `<root>/repo`: `<product-python> scripts/run-alpha-pv.py --run lifecycle
  --run-id ALPHA-L01-DEV-20261003-02 --config <root>/m4c-product-config.yaml
  --fixtures <root>/fixed-pcm/fixtures.json --output <root>/lifecycle-02 --watchdog 900
  --network-launcher sudo-unshare`.
- **PASS**, exit 0: three Sessions, six Turns, three Session-start Buttons; all per-Session cleanup
  barriers; graceful shutdown; all product process/hardware-owner absence checks; fresh-process
  clean-IDLE restart. Network attempts/fallbacks and aggregate privacy matches are all zero.
  Public result: `<root>/lifecycle-02/result.json`; actual logs/observations remain private under
  `<root>/lifecycle-02/private/`. This is development convergence, not formal ALPHA acceptance.

#### Regression and content reconciliation

- Workstation focused driver/prompt/privacy/config tests: **134 Pass**, exit 0.
  Compile and `git diff --check`: Pass. An earlier combined runner invocation had 56 Pass / 3 Fail
  because its unchanged Linux process/watchdog tests require `/proc`, absent on this macOS host;
  those tests execute on Pi below. Failure records are not relabeled.
- Pi portable Python: `/home/<operator>/m4b-test-runtimes/py313/bin/python`, 3.13.15, pytest 9.1.1.
  `PYTHONPATH=src <python> -m pytest -q tests/test_alpha_product.py tests/test_alpha_pv_runner.py
  tests/test_m4b_prompt_001.py tests/test_m4b_priv_001.py tests/test_m4b_cfg_001.py -o addopts=''`:
  **179 Pass**, exit 0; raw log `<root>/focused-regression.log`.
- Complete Pi non-RPi suite, `PYTHONPATH=src <python> -m pytest -q -m 'not rpi' -o addopts=''`:
  **1948 Pass / 1 Fail / 35 deselected**, exit 1, 55.29 s. The sole failure was retained-history
  test G06 because `git archive` omits repository history; raw log `<root>/non-rpi-regression.log`.
  Added existing Git history through standard Git commands, preserving all product files, then
  reran that one test: **1 Pass**, exit 0; `<root>/retained-history-regression.log`.
  No Fail/Skip/XFail remains among the applicable tests after that infrastructure correction.
- Pi `compileall` and `git diff --check`: Pass. One independent transfer-boundary checksum-mode
  `rsync -nrcRi` found no workstation/Pi content difference for the eight modified code/test/profile
  files. This operator comparison is not a run assertion or startup operation.

#### Diagnostic record and measured feedback

- [IR_dev_ALPHA_II](../reviews/history/IR_dev_ALPHA_II.md) is Resolved and preserves the initial
  finding, native diagnostic comparisons, USER wording proposal and measured resolution.
  Original arithmetic ASR-form answers were wrong and ended with or without JSON constraint.
  Original prompt routing varied with punctuation/topic; a longer clarification proposal failed.
  USER's two-character addition changed the three ordinary diagnostic requests from true to false
  while preserving true for explicit end. It did not correct the original arithmetic answer.
- Native-only private diagnostic logs remain under
  `/home/<operator>/alpha-lifecycle-fix-20261003-BB29MH/`: `prompt-proposal-diagnostic.log`,
  `question-constraint-debug-01.log`, `question-punctuation-debug-02.log`,
  `two-turn-debug-03.log` and `prompt-user-wording-debug-04.log`. They do not substitute for hardware
  or Quality evidence.
- Initial candidate failures remain under `/home/<operator>/alpha-dev-20261003-ZSKsbM`:

| Run ID | Result / exit | Preserved outcome |
| :--- | :--- | :--- |
| `ALPHA-L01-DEV-20261003-01` | FAIL / 2 | First Turn chose END_SESSION, leaving Turn 2. |
| `ALPHA-P01-DEV-20261003-01` | INVALID / 2 | P02 ended early; complete P01–P05 baseline missing. |
| `ALPHA-R01-DEV-20261003-01` | FAIL / 2 | Child failure/replacement observed; new Session ended before its second Turn. |
| `ALPHA-Q-DEV-20261003-01` | FAIL / 2 | Q01 completed; Q02 ended and hit unconditional runner close; Q03–Q06 unexecuted. |

- Initial public evidence is `<old-root>/<run-name>-01/result.json`; raw logs/observations are in
  each sibling `private/`. All initial final owner-cleanup booleans were true. Their runs remain
  failed/invalid; the revised Lifecycle Pass is a separate new-content run.
- Subsequent document feedback: synchronize M4B prompt wording/token metadata and ALPHA/Test Spec
  `FX-SHORT-A` with the measured revision above. USER explicitly removed a preceding Designer gate.
- Performance subsequently obtained a valid baseline on v3 and Recovery passed on v4, as recorded above.
  Quality on v4 failed two semantic criteria; its repair and final common-candidate Pi Verify/ALPHA
  acceptance and commit remain pending.
  No commit or push was made; `current.md` remains Designer-owned.

## Last completed M4C implementation (retained record)

### Authority and scope

- Developer entry is Open by `docs/status/current.md`. Product authority is
  `docs/milestones/M4C.md`; executable authority is `docs/test_spec/test_spec_M4C.md`.
- The Pi catalog is exactly seven automatic sub-runs: S01, S02, S03, the three S04 variants and S05.
  S06/S07 are portable integration coverage. S08 adds no test or implementation. S09 is subsumed by
  S02, `M4C-SS-CTRL-001` C14/C15 and S04/ACTION. There is no human-result field.
- Assertions retain only stated product risks. Runtime scenarios do not calculate source, model, artifact,
  evidence or text digests. The content comparison below is a single candidate-transfer diagnostic.

### Final implementation result

- `scripts/run-m4c-pv.py` now contains only the seven authorized entries. Result validation forbids
  `user_result`; finalization requires one designated automatic Pass for every entry and rejects unknown,
  missing or duplicate active variants. Runner tests execute the exact seven-entry finalizer.
- `M4C-PI-S01/START_IDLE` is implemented in the exact-product Pi driver. It starts the real product graph,
  observes a bounded IDLE window, and requires no Session, no audio capture, no perception or error,
  Status `IDLE` (`待命`), empty Main and an open Display resource before orderly shutdown.
- S02 operator prompts are instructions only. Its THINK Main ledger now derives both expected values from
  the actual `PerceptionResult.text`; it does not compare ASR output with the prompted sentence. Terminal
  answer, synthesized speech and final Display answer equality remain unchanged and private text is not
  projected publicly.
- S06 cases are traced as `M4C-SS-OUTCOME-001/O08` and O09. O09 exposed retained StreamingSpeak inflight
  fragments after a TTS worker fault; the fault path now clears pending bytes, inflight fragments and PCM
  before publishing exactly one error. S07 is traced as `M4C-DISPLAY-001/D01` and proves one Display failure
  cannot interrupt two complete LLM→TTS→Audio turns or prevent final IDLE.
- The complete regression run exposed one pre-existing positional `LLMResponse` construction in the S04
  try-run. It is now keyword-only and passes the retained M4B structural anti-weakening gate; product behavior
  is unchanged.

### Verification result

- Workstation:
  - Focused runner, S02, S04, S06/S07 and M4C regression tests: Pass.
  - `PYTHONPATH=src xargs -a tests/m4c_portable_suite.txt .venv/bin/python -m pytest -q`:
    **529/529 Pass**.
  - `PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not rpi'`:
    **1890/1890 applicable Pass**, zero Skip/XFail.
  - `PYTHONPATH=src .venv/bin/python -m compileall -q src scripts tests` and
    `git diff --check`: Pass.
- Pi target, Python 3.13.5, isolated checkout `m4c-final-dev-20260926-A0dIDk`:
  - M4C portable catalog: **529/529 Pass**.
  - Complete non-RPi regression: **1890/1890 applicable Pass**, zero Skip/XFail.
  - `M4C-PI-S01/START_IDLE` attempt `M4C-S01-START-IDLE-20260926-02`: **Pass** in 5.05 s;
    public evidence reports `IDLE_READY`, no Conversation, no capture, Display open and Main empty.
    Evidence locator is `M4C-FINAL-DEV-20260926/M4C-PI-S01/M4C-S01-START-IDLE-20260926-02`.
- The final implementation-content comparison excludes `.git`, virtual environments, caches and this
  self-reporting status file. Workstation and Pi both produce SHA-256
  `d9f0c34aafe19be0ebf55b5b3ef22bf4ca6b0be1d591ab42b68e42b2dda2b9ee`; checksum-mode `rsync -anic`
  reports no file-content difference.

### Blocker and next action

- No implementation blocker remains. S02–S05 development hardware runs are already recorded by their
  existing scenario IDs; completed history is not repeated here.
- Next owner is Tester/Verify for the formal seven-sub-run M4C Pi PV and finalizer. The implementation is
  ready for one milestone commit proposal; commit and push still require explicit USER approval.
