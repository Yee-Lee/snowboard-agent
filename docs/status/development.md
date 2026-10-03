# Current development status

## Active ALPHA implementation

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
