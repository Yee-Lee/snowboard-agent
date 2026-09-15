# Current development status

## Completed seven-ID Pi PV and Designer verification handoff — 2026-09-15

- Developer ran the final same-tuple `PV-M4B-FINITE-03` on Raspberry Pi 5
  (`pi5-4gb-debian13-aarch64-cp3135`), then read the entire public final
  manifest. Protected content/harness/profile digests are
  `f6b9cfe2dcadeac675deb4811b2711e9c0c6a28d73e4985fc9ae321fb08c7545`,
  `cb79a96c06cdf427142fd9171523ce545e2b35951c59117d9d1dc8cf95988b33`,
  and `8d957a4600fc172fd7dd7b285098710af0b753d7d1b697a21bd31611637b3f90`.
  Public evidence: Pi-local `m4b-pv-finite03-public/pv-final.json`; private
  bound evidence: Pi-local `m4b-pv-finite03-private/pv-final-manifest.json`.
- Finalizer returned `pv_status=Pass`, with seven script `Pass`, six applicable
  Developer review `Pass`, and #2 S01/S02/S03 USER `Pass`; all seven selected
  Test IDs have empty `reason_codes`. Review counts (fields/rows) are #1
  `368/114`, #3 `410/146`, #4 `22,607/5,448`, #5 `1,612/573`, #6 `359/123`,
  and #7 `60,388/16,005`. #2 selected S01 `SEM-S01-F03-A03`, S02
  `SEM-S02-F03-A01`, and S03 `SEM-S03-F03-A01`, preserving earlier S01 attempts.
- #4 observed 241 finite two-turn samples, normal close, MemAvailable
  `2,786,115,584–3,300,950,016` bytes, temperature `49.6–56.2 C`, and no
  OOM/throttle event. Its Speak/Generate estimates are `585,105,408`/`732,954,624`
  bytes (558/699 MiB); swap used grew `85,360,640→87,457,792` bytes and was
  recorded only, not graded. Native context exhaustion/replacement was not
  observed by #4, so these are finite-session estimates, not replacement proof.
- Tester revised current Test Spec §5.1 after the Pi finalizer: #1 ATT verifies
  its own bound identity, offline flags and child `network_denial_installed`,
  without claiming zero network attempts or requiring duplicate syscall capture.
  The separate #7 `R01-OFFLINE` case owns pre-native-through-exit syscall tracing
  and zero-external-attempt evidence (160 captured trace files). Product §11.2
  maps #1 to identity and #7 R01 to actual network attempts; no Product, runner,
  model or profile byte changed for this clarification. The prior #1 wording
  discrepancy is resolved under the current mapping, subject to Designer Verify
  of the Tester-owned revision; neither Test ID borrows the other's card/result.
  Remaining review caveats: #5 uses controlled stimulus/display
  endpoints, not physical wake/display proof; #7 R05 close proof is the approved
  indirect fail-closed product-gate evidence, R06 had no initial descendant, and
  R07 proves owner lifecycle rather than full product shutdown.
- Next owner: Designer for `Verify` of this completed Pi runner result and the
  listed caveats. No commit or push was made; workstation same-byte reconciliation
  and USER-approved milestone commit remain separate requirements. Detailed
  experiments, raw values, partitions, blockers and review locators are in the
  existing root `update_m4b_pv.md`; no new handoff document was created.

## Active POC-schema and PV correction — 2026-09-15

- Current Designer/Product/Test Spec narrow correction: #3/#4 now use separate genuine
  two-turn Product Sessions (`C01-FIRST`, `C02-CONTINUE`) and normal application-owned
  close (`C03-CLOSE`); controlled portable `M4B-CONV-001` `C02`–`C05` retain
  deterministic rejection/replacement coverage without claiming native context
  exhaustion. Affected paths: `scripts/run-m4b-pv.py`,
  `scripts/m4b_target_metrics.py`, `tests/test_m4b_pv_runner.py`,
  `tests/test_m4b_measurement_harness.py`, this status; Test IDs #3/#4 plus
  directly affected portable CONV/OUTCOME/MEM cases. Estimate: 3 points.
  Verify affected portable tests, fresh independent native #3/#4 and complete
  raw-evidence Developer review on the same pending Pi bytes; no commit yet.
- First finite Pi diagnostic `PV-M4B-FINITE-01/CONV-01` passed #3 script and
  Developer inspection (410 fields/146 rows): real native JSON `end=false`
  twice, same child PID/PGID 7604 and generation 1, revision 0→1→2,
  second-turn KV 112, matching three-part normal close and cleanup. Independent
  `MEM-01` produced 253 valid samples and script Pass with finite estimates
  Speak 579,862,528 / Generate 705,691,648 bytes. Developer inspection found
  the required setup `SwapTotal` absent from its private series despite the
  captured swap-used trajectory; no #4 Developer Pass was recorded. The narrow
  runner correction now records exact setup SwapTotal bytes and swappiness,
  so this diagnostic tuple cannot be final same-byte credit. Fresh Pi #3/#4
  and complete review are pending.
- Corrected finite diagnostic `PV-M4B-FINITE-02` #3 again passed Pi script and
  Developer review (410 fields/146 rows). #4 independently passed script with
  270 complete samples, exact setup SwapTotal 2,147,467,264 bytes and
  swappiness 60, and finite Speak/Generate estimates 612,368,384 /
  710,934,528 bytes; every sample/owner, lifecycle boundary, native output,
  controller trace and integer formula was independently checked. Recording
  #4 Developer review exposed a runner capacity defect: its 3,635,477-byte
  complete inspection catalog exceeded `_read_json`'s 1 MiB default and
  misleadingly returned `M4B_PV_BINDING_INVALID`. The narrow correction keeps
  binding JSON at 1 MiB and permits only inspection catalogs up to 16 MiB,
  with a directly affected regression. `FINITE-02` remains diagnostic, not
  final same-byte credit; fresh Pi validation and review are pending.
- USER removed the active-zram zero-growth stop. Developer removed only swap-growth
  rejection in `SystemResourceSample.validate`, measurement startup and PV resource
  health; swap deltas remain measured. OOM/kernel fault, 512 MiB laboratory floor,
  thermal, throttling, PID/identity, sampler and cleanup stops remain. Directly
  affected workstation and Pi focused suites each passed 167/167. Current Product
  §5.3 and focused Test Spec M02/M04/R02 now map this exact change.
- `PV-M4B-CURRENT-01` #1 ATT script Pass and Developer Pass after complete inspection
  of 368 fields and 114 rows, but its protected tuple predates the swap fix and
  cannot be credited to the later `PV-M4B-SWAPFIX-01` tuple. Its #3 `CONV-02`
  returned Incomplete on the old swap predicate: baseline/post swap
  34,717,696→37,863,424 bytes, MemAvailable 2,942,484,480→2,893,807,616 bytes,
  temperature 49.6→53.45 C, OOM 0→0, throttle 0→0, stable owner PID identities;
  native output was normal non-empty `end=false`. A prior `CONV-01` stopped before
  inference because the pytest venv lacked pyalsaaudio; subsequent Product runs
  use the configured controller Python and keep both failed attempts.
- With normal `/dev/zram0` enabled and swappiness 60, swap-fixed #3
  `PV-M4B-SWAPFIX-01/CONV-01` proceeded through eight real native generations
  without swap E1, then returned Incomplete at `M4B_PV_FILL_TURN_FAILED`.
  `C01-FIRST` and `C02-FILL-0001` through `0006` were non-empty `end=false` /
  `KEEP_NEXT`; `C02-FILL-0007` was non-empty `end=true` / `END_SESSION` at
  `current_kv_tokens=376`, incremental 17, reserve 128 of Engine 1024. No context
  admission rejection or replacement had occurred. Raw trace and child output
  are in Pi-local `m4b-pv-swapfix01-private/conv-01/`; public Incomplete card
  is in Pi-local `m4b-pv-swapfix01-public/conv-01/result.json`. This is a
  separate scenario/product-end decision for Designer/Tester; Developer will not
  override real `END_SESSION`, replay generations or credit #3 as Pass.
- Latest aligned tuple `PV-M4B-ALIGNED-01` has #1 ATT script + Developer Pass
  (all 368 fields/114 rows reviewed) and #6 TIME script + Developer Pass
  (all 359 fields/123 rows reviewed). #6 used the fixed 103,724-byte WAV:
  ASR `請簡短介紹台灣。`, native non-empty `end=false` Taiwan response,
  prefill 86/decode 26, Product Speak/KEEP_NEXT, TTS/Audio action OK and close
  cleanup true. Ordered controller-monotonic timeline has exact null reason
  `NOT_APPLICABLE` for first-safe text; no latency ceiling was invented.
- On the same aligned tuple, #4 `MEM-01` is Incomplete: eight Product generations
  were structurally successful until the deterministic `C02-FILL-0007`
  native `end=true`/`END_SESSION` at KV 376 + incremental 17 + reserve 128 of 1024,
  before context rejection/replacement. Private `mem-series.json` preserves 835
  points (Engine-ready through eight primary completions), MemAvailable range
  2,817,671,168–3,276,996,608 bytes, swap used range
  69,320,704–79,806,464 bytes, temperature 47.4–57.85 C, OOM 0, throttle 0,
  one stable owner-PID set, cleanup true. `completed=false`,
  `estimates_reason=SUB_RUN_INCOMPLETE`; all four public estimate fields are null.
  The same early model end blocks both #3 replacement evidence and #4 complete
  threshold estimates; no rerun/prompt-only bypass or fabricated estimate.
- Aligned #5 WAKE designated cases `W01-A01` through `W04-A01` each have Pi
  script Pass and inspected raw capture: W01 OPEN-first, W02 ACK-first and W03
  slow-OPEN all kept Listen/ASR/frame pull later than both Conversation join and
  wake acknowledgement; W03 recorded a bounded OPEN delay of 200,137,836 ns.
  W04 interrupted OPEN with `activity=[]`, no wake/Conversation join barrier,
  no Perception/admission and cleanup true despite a stale native READY.
  Display remained state-slot-only with no Session content. Its Pi Test-ID
  aggregate script Pass and Developer Pass followed full inspection of 1,612
  fields/573 rows across the four captures and five public cards. An earlier
  transient aggregate-call reviewer-capacity rejection was retried on the same
  command and did not represent a runner failure.
- USER explicitly directed Developer to start despite the stale closed entry in
  `docs/status/current.md`. Tester has remapped the exact 352-byte POC schema in the
  current `test_spec_M4B.md`; no earlier regex or invented-schema tuple is evidence.
- Affected paths: `requirements/m4b/semantic-output-v1.schema.json`, product profile
  and artifact lock, `src/sbd/cognition/semantic.py`, LiteRT worker/lock and READY
  protocol, `scripts/run-m4b-pv.py`, directly affected portable/PV-runner tests and
  this Developer status. Affected Test IDs: `M4B-PROMPT-001`, `M4B-SEM-001`,
  `M4B-S2-001`, `M4B-WIRE-001`, `M4B-OUTCOME-001`, `M4B-REG-001` G07–G10 and
  Pi #1–#7. Estimate: 6 points for schema/identity, runner disposition/catalog,
  #3 lifecycle correction and same-bytes Pi convergence.
- Planned checks: focused portable and PV-runner regressions on the workstation and
  Pi CPython 3.13.5; direct native POC-schema generation; fresh independent Pi
  #1–#7 runs, complete printed evidence/Developer review for #1/#3–#7 and USER
  semantic verdicts for #2. No matrix per USER direction; no commit before Pi Verify.
- Designer `to_developer.md` findings 1–5 are accepted as directly affected work:
  exact catalog/evidence binding, result-state reduction, private-only commentary,
  canonical PV-runner collection and raw/decoded 4096-codepoint terminal boundary.
  The exact schema file/profile/lock/READY path is now implemented; Pi focused
  227/227 passed before the boundary addition. The boundary is implemented and
  its new focused test passes 30/30 on the workstation.
- Native POC-schema #3 diagnostics `CONV-POC-01/02` are Incomplete before the first
  successful Product turn: each child selected JSON and produced the same normal
  non-empty `end=false` Taiwan text, but the post-generation resource sample saw
  zram growth (0→18 MiB, then 12→14 MiB) and correctly raised E1 under current
  Product §5.3. Cleanup was proven. Temporarily setting swappiness=1 did not stop
  growth; Pi was restored to 60. These diagnostic attempts are not PV credit.

## Active single-PV implementation — 2026-09-13

- Entry: Open by `docs/status/current.md`; focused `TR_spec_M4B_IX` is Resolved and current
  `test_spec_M4B.md` maps the non-empty model-text correction. USER excludes human Test ID #2
  from this development completion and directed automated #1/#3/#4/#5/#6/#7 to completion.
- Active Test IDs are #1 `M4B-PI-ATT-001`, #3 `M4B-PI-CONV-001`, #4
  `M4B-PI-MEM-001`, #5 `M4B-PI-WAKE-001`, #6 `M4B-PI-TIME-001` and #7
  `M4B-PI-RES-001`; #2 `M4B-PI-SEM-001` remains implemented but intentionally unexecuted.
- Implemented the mapped non-empty response contract: GBNF and native regex use `char+`, both
  `end=false` and `end=true` require normalized non-empty text, and empty output retains the existing
  R2 cleanup/replacement route. Grammar SHA-256 is
  `fe97dc391364d875b9955cdfb283bd160b7845eae1e63734075da806973207b3`; profile SHA-256 is
  `988077ebe480a6dbf7f0453603fe328675d13baa278f2ce27b9e541fccbcccb7`.
- Corrected #3 C06 completion to accept either structurally valid following-turn route instead of
  adding an unsupported `end=false` requirement. The canonical PV runner applies the USER-selected
  25% S16_LE playback gain only to runner-created Audio output; production Audio output and shared
  Audio configuration remain unchanged.
- Focused PROMPT/SEM/S2/OUTCOME/GEN/PV-runner regressions passed **225/225** on the workstation and
  **225/225** on Pi CPython 3.13.5. No matrix was run as directed by USER.
- Final native Pi tuple `PV-M4B-AUTO-02` is bound to protected-content digest
  `1c4ea3c2daf2e87893806a4f2fa7a8f9ceeb19822918f7f1852452c0e8f750f7` and harness digest
  `c6a4f3facdeb85b6fd08485ea5b6113a578347ea5ead1fd0a4b490fe275be9a8`.
  Workstation and Pi recomputation match the binding exactly.
- Final native results: #1 ATT Pass, #3 CONV Pass, #4 MEM Pass, #5 WAKE W01–W04 plus aggregate
  Pass, #6 TIME Pass, and #7 RES R01–R08 plus aggregate Pass. Public cards are under
  Pi-local `m4b-pv-auto02-public`; access-controlled captures and binding are under
  Pi-local `m4b-pv-auto02-private`. Pi zram was restored with zero used bytes and
  `vm.swappiness=60` after execution.
- All prior PM/PR/PH/replay outputs remain rejected. Every sub-run/case uses a new identity and
  empty access-controlled partitions. No automatic semantic verdict, legacy threshold/profile,
  role approval artifact or cross-Test-ID evidence is accepted.
- Developer completion is **6/6 USER-scoped automated Test IDs Pass**. #2 remains for USER execution;
  therefore the seven-ID finalizer was intentionally not run and no overall `PV PASS` is claimed.
  No protected file may change without invalidating this tuple and requiring applicable Pi reruns.

## Superseded pre-PV PM/PR/PH runner correction — 2026-09-13

- USER superseded debugging with two bounded voice scripts: exactly one or two microphone
  windows, 10 seconds each, no automatic filling or PM/PR/PH verdict. Stop background replay.
  Scope: measurement runner optional diagnostic_windows, harness optional no-profile collection,
  two shell launchers and focused Pi regression. Estimate 1 point. Retain default production
  timeouts and report actual failures; do not claim unresolved native latency fixed.

- Active native failure correction: USER run user-pm-22clsQ stopped during first generation
  at resource.validate_sample, with the rejected sample absent from diagnostics. Prior 199
  regressions are insufficient native evidence. Affected resource.py, measurement recorder,
  resource regressions and temporary Pi replay driver. Preserve rejected sample + previous
  sample + validation reason; investigate coherent proc snapshots and native cleanup proof.
  Estimate 2 points; verify focused Pi 3.13.5 tests and actual model/audio replay through
  context rejection/replacement before returning the human launch command. No commit.

- Latest USER override: at most five human microphone windows; real model-generated automatic
  context filling is explicitly permitted. Label automatic inputs separately; preserve the real
  1024-token context, real admission rejection and replacement. Affected runner and harness tests;
  verify on Pi Python 3.13.5 before handing back the same launch command.
- Current correction: remove suggested/fixed questions and ASR equality/repeat gates.
  All five microphone windows accept free input; automatic filling starts after two windows
  even with ASR timeouts. Preserve silence/typos for agent review, without a sixth window.
  Affected paths: scripts/m4b_measurement.py, tests/test_m4b_measurement_harness.py and
  deployed run-user-pm.sh; same focused Pi command below. Estimate: 1 point.
- Five-window implementation verified: two microphone turns, explicit automatic text turns
  through Reasoner/worker admission and native generation in deployed runtime, real context
  rejection, replacement, then three free-input microphone windows.
  Automatic rows carry input_source=automatic_fill and audio_turn=null; microphone rows retain
  their independent PCM numbering. No context/token limit is changed.
- Pi focused regression (runner/offline/admission/resource/candidate consumer): **199 passed**,
  12.95 s on CPython 3.13.5. Includes the USER-reported five-window transcript/timeout sequence,
  free wording after replacement and five empty windows without asking for a sixth.
  Boundary fixture uses a deterministic runtime and is not native PM
  evidence. Workstation/Pi runner and test hashes match; launcher shell syntax and executable
  permission verified. Runner SHA-256:
  `b4b71be5cc51395af05564b7603be506931e3c3cf8b90b1b3715a06eb2b628e5`.
  Real user PM is still pending and no PR/PH acceptance is claimed.

- USER explicitly requested implementation despite the stale closed entry in current.md.
- Active scope: measurement orchestration, diagnostic persistence, artifact verification timing,
  replacement evidence, free input, and truthful PM/PR/PH completion reporting.
- Affected paths: scripts/m4b_measurement.py, cognition/litert_lm/worker.py,
  tests/test_m4b_measurement_harness.py, tests/test_m4b_off_001.py, this status.
- Test IDs: M4B-PI-MEM-001, M4B-PI-CONV-001, M4B-PI-TIME-001, M4B-PI-RES-001.
- Estimate: 5 points; verify focused runner/worker regressions on Pi CPython 3.13.5,
  then native and user-driven verification on the final content digest. No commit before Pi Verify.
- PM, PR and PH are pending. Existing fake-worker tests do not establish native recovery or PH.
- PM runner revision: user-selected 10-second capture windows; empty ASR retries without
  Reasoner input; explicit transcript/response display; first-frame READY; no literal or semantic
  repeat assertion, zero-KV observation after replacement; interruption bundles; post-cleanup artifact
  verification; PM handoff inventory with read-back hashes and rederived release thresholds.
- Pi CPython 3.13.5 focused runner/offline/admission/resource regressions: 117 passed.
  Actual deployed model/runtime artifact verification also succeeded without starting audio.
  Native user PM remains to be executed; no PR/PH completion or M4B closure is claimed.
- USER removed automatic PR/PH execution from scope. PM exports are checked with
  `scripts/m4b_measurement.py --validate-pm <private-output>`; PR/PH remain separate execution/review.
- Consumer alignment scope: scripts/candidate_gate.py and tests/test_candidate_gate.py,
  M4B-PI-MEM-001. Replace obsolete approval-dependent input with the PM runner's
  automatic attestation and exact saved series format; retain all release/recovery checks.
- Latest USER direction: agent reviews PM evidence; automatic reporting is advisory and must
  not force a new recording after a completed capture. Postprocessing exceptions now preserve
  raw/partial outputs with NeedsReview and capture_complete, without claiming PR/PH Pass.
- Final focused Pi CPython 3.13.5 command: `PYTHONPATH=src:. timeout 180
  ${PI_HOME}/m4b-dev.fLl6tj/venv/bin/python -m pytest -o addopts= -q
  tests/test_m4b_measurement_harness.py tests/test_m4b_off_001.py tests/test_m4b_adm_001.py
  tests/test_m4b_res_001.py tests/test_candidate_gate.py`: **196 passed**, 12.97 s.
- Launch remains `${PI_HOME}/m4b-target-20260913-sLrXyC/run-user-pm.sh` on snowboard-rpi5.
  Completion marker is PM_CAPTURE_COMPLETE, meaning collection finished for agent review,
  not PM/PR/PH acceptance. PR input export and the existing consumer use the same saved series
  bytes and automatic attestation; release recovery checks remain required in PR.

- Updated: 2026-09-13
- Owner: Senior Developer / integration owner
- Scope: `CR_M4B_II` B2, deterministic canonical collection under repository pytest addopts
- Starting SHA: `1eefd97dd9866f804d07be6aacddb6948d05b6e1`
- Status: **B2 correction complete; Revised for new append-only candidate verification**
- Next owner: Tester, after USER-authorized append-only commit creates a new exact candidate
- Candidate: rejected provisional SHA `1eefd97dd9866f804d07be6aacddb6948d05b6e1`;
  no replacement commit, push, Pi measurement PASS or human acceptance is claimed

## Active B2 correction inventory — 2026-09-13

- Affected paths: `scripts/candidate_gate.py`, `tests/test_candidate_gate.py`, this Developer
  status and active `docs/reviews/CR_M4B_II.md` only. Tester/Designer-owned files remain unchanged.
- Affected symbol: `_m4b_collect_nodes`; exact regression fixture exercises a repository whose
  `pyproject.toml` sets pytest `addopts = "-q"`.
- Mapped Test ID: `M4B-REG-001` G02/G04/G05 collection and evidence identity.
- Estimate: 1 point. Minimal correction makes collection verbosity independent of repository
  addopts while retaining canonical selectors, marker filter, timeout and duplicate/missing-node
  rejection.
- Bounded verification: focused B2 regression, complete `tests/test_candidate_gate.py`, Python
  compilation and `git diff --check`, each with an outer timeout.

## B2 correction result

- `_m4b_collect_nodes` now invokes pytest with `-o addopts=` before its own single `-q`.
  Repository `addopts` therefore cannot silently combine with runner verbosity, while the runner
  still owns the exact canonical selectors, `not rpi` marker filter and collection timeout.
- `candidate_repo` now places `addopts='-q'` in `pyproject.toml`; the executable canonical-run
  regression asserts that the result contains exactly 13 node IDs in `path::node` form. Without
  the correction, pytest 9.1.1 applies effective `-qq`, emits per-file counts and the runner raises
  `M4B_COLLECTION_INVALID` before execution.
- CPython 3.13.15 / pytest 9.1.1 focused canonical regression: **1 passed**, exit 0, 0.75 s.
- CPython 3.13.15 / pytest 9.1.1 complete `tests/test_candidate_gate.py`: **78 passed /
  0 failed / 0 error / 0 skipped / 0 xfailed / 0 xpassed**, exit 0, 13.21 s.
- `python -m compileall -q scripts/candidate_gate.py tests/test_candidate_gate.py`: exit 0.
- These are Developer regressions only. Because the candidate runner and test fixture are protected
  inputs, SHA `1eefd97dd9866f804d07be6aacddb6948d05b6e1` and its partial Pi run remain rejected.
  A new append-only candidate and complete independent Linux matrix are required; PM/PR/PH remain
  Pending.

## Active B1 correction inventory

- Affected paths: `scripts/candidate_gate.py`, `tests/test_candidate_gate.py`, this Developer
  status and active `docs/reviews/CR_M4B_II.md` only. Existing Tester-owned
  `docs/test_spec/test_spec_M4B.md` and Designer-owned `docs/status/current.md` changes are
  preserved and not edited.
- Affected symbols: `suite_counts`, `passed`, `portable`, `run_suite`,
  `validate_version_result`, `validate_matrix`, `matrix`, plus new candidate-owned catalog,
  collection, JUnit, platform/profile and per-Test-ID evidence validation helpers.
- Mapped Test ID: `M4B-REG-001` G01/G02/G04/G05/G06; the evidence index additionally proves
  execution identity for all 13 current portable Test IDs.
- Estimate: 3 points (runner enforcement, negative regression fixtures, focused verification).
- Bounded verification commands: `timeout 180 python -m pytest -o addopts='' --strict-markers
  --timeout=120 -q tests/test_candidate_gate.py`; focused B1 negative tests under the same outer
  timeout; `timeout 60 python -m compileall -q scripts tests/test_candidate_gate.py`; and
  `git diff --check`.
- Explicitly out of scope: D1/D2 Darwin behavior and any committed macOS skip/xfail; USER's
  diagnostic-only disposition remains unchanged. Linux CPython 3.11/3.12/3.13 formal reruns are
  independent Tester work after a new candidate exists.

## B1 correction result

- `suite_counts` now records failures and errors separately and parses exact pytest `xfailed` and
  `xpassed` totals. `passed` and both portable/matrix gates require zero for all five forbidden
  outcomes; a real XPASS probe now exits nonzero and writes `status=Fail`, `xpassed=1`.
- M4B portable execution is bound to the exact tracked
  `tests/m4b_portable_suite.txt`. Absolute, repo-external, directory and arbitrary file selectors
  are rejected before pytest; generic pre-M4B candidate-gate behavior remains available only to
  repositories without the M4B product-profile authority.
- The formal M4B runner independently collects the canonical nodes and audits affected sources,
  exact 99-node Foundation evidence and the resulting JUnit. Its result binds Linux
  x86_64/aarch64, exact CPython minor/full version, profile ID/digest, catalog paths/digest,
  collection count/digest, JUnit digest, monotonic bounds, raw logs and all 13 portable Test IDs.
- Matrix aggregation reopens every result/JUnit/collection/log locator under its version evidence
  directory, rejects traversal/symlinks/missing files, recomputes digests and audits, and binds the
  index to result, profile and catalog digests. Negative coverage rejects mixed platform, suite,
  catalog, profile, Test-ID, JUnit and XPASS records.
- Focused Developer verification used outer 180-second process bounds and pytest's 120-second test
  timeout. CPython 3.11.16, 3.12.14 and 3.13.15 each returned **78 passed / 0 failed / 0 error /
  0 skipped / 0 xfailed / 0 xpassed** for `tests/test_candidate_gate.py`. A focused
  `M4B-REG-001` run excluding only USER-disposed Darwin G05 returned **15 passed / 1 deselected**.
  The synthetic canonical execution test itself produced **13 passed** with all 13 Test-ID rows and
  exact **99 retained / 0 missing** Foundation evidence.
- CPython 3.11.16/3.12.14/3.13.15 `python -m compileall -q scripts
  tests/test_candidate_gate.py`: each exit 0. `git diff --check`: exit 0.
- These are Developer regression results, not formal candidate evidence. The rejected SHA remains
  immutable; protected runner/tests changed, so all earlier portable diagnostics and matrix output
  are invalidated. Tester must independently execute the complete Linux CPython
  3.11/3.12/3.13 canonical matrix against the new exact candidate. PM/PR/PH remain Pending.

## Authority and result

Developer entry was opened after Designer resolved `IR_dev_M4B_IV` and Tester resolved
`TR_spec_M4B_VII`. The implementation uses only the authorized explicit
`DISCARD_TICKET` / `TICKET_DISCARDED` transition. It does not supersede tickets implicitly and
does not use `CLOSE` to preserve a Conversation after R1.

WP-01 through WP-06 are implemented and integrated. The Linux/aarch64 target portable catalog,
immutable baseline, affected shared paths, full non-hardware repository regression, compilation
and diff checks pass. The measurement-only target entry is implemented but remains fail-closed:
native PM and human rows require a clean exact-SHA candidate, target artifacts and independent
Designer/Tester authorization.

## Implemented path and symbol inventory

### WP-01 — profile, prompt and config

- `src/sbd/cognition/{prompt_builder,semantic,factory}.py`: frozen V2D2 prompt identity,
  listen-only projection, normalization/semantic parser and real adapter construction.
- `src/sbd/cognition/litert_lm/lock.py`, `src/sbd/core/config/{loader,models,validate}.py`,
  `config.example.yaml`: exact profile/runtime/artifact attestation and rejection of legacy keys.
- `requirements/m4b/{llm-artifacts.json,llm-runtime-rpi-cp313.json,product-profile.json,semantic.gbnf}`:
  locked runtime/artifact schemas and null-threshold measurement profile.
- `scripts/{m4b_inheritance,m4b_llm_product}.py`: deterministic inheritance and release-only
  product validation.

### WP-02 — child protocol and adapter

- `src/sbd/cognition/llm.py`, `src/sbd/cognition/llm_child_protocol.py`,
  `src/sbd/cognition/litert_lm/{adapter,worker,measurement}.py`: typed v3 lifecycle,
  non-mutating MEASURE, exact discard acknowledgement, permanent one-use ticket identities,
  GENERATE-only mutation, cancellation scrub, close/shutdown proof and bounded PGID cleanup.
- `tests/fakes/m4b_llm_child.py`: real subprocess/barrier fault fixture for framing, disposal,
  cancellation, recovery and descendant cleanup.

### WP-03 — Reasoner product policy

- `src/sbd/cognition/reasoner.py`, `src/sbd/core/state_manager/notices.py`: exact admission and
  outcome matrix, speech ownership, KEEP/REPLACE/END routing, one generation/Fact maximum,
  repeated R2 behavior and fixed public notices.
- `src/sbd/core/state_manager/manager.py`: private-input lifetime control and post-close recovery
  authorization without a public state/Event/Fact change.

### WP-04 — planned recovery and composition

- `src/sbd/core/{m2_composition,_m4b_resource_binding}.py`: real Audio/ASR/TTS/LLM composition,
  owner registry, READY/replacement resource proof and same-key RM barrier.
- `src/sbd/action/rest/action.py`: private completion callback at the actual Rest worker boundary;
  stale Facts cannot complete a new observation and callback failure emits no fake success.

### WP-05 — observability, privacy and tooling

- `src/sbd/cognition/observability.py`, `src/sbd/cognition/litert_lm/resource.py`: allowlisted
  prompt/runtime/memory/timing rows, explicit null reasons, unique-PID PSS attribution and target
  health sampling. Native timing is used only after Linux clock/time-namespace proof.
- `src/sbd/perception/listen/listener.py`, `src/sbd/action/speak/speaker.py`,
  `src/sbd/core/audio/alsa/output.py`: actual ASR-final, PCM-ready and first-positive-write hooks.
- `scripts/{m4b_target_metrics,m4b_measurement}.py`: bounded measurement series, cleanup watchdog,
  private `0700`/`0600` outputs, exact dual-review grant and fail-closed native session. It cannot
  produce release or human PASS cards.

### WP-06 — verification and cutover guards

- `scripts/candidate_gate.py`, `tests/m4b_portable_suite.txt`, `tests/m4b_target_cases.py`:
  replacement catalog, evidence validation and explicit target-input binding.
- `tests/test_m4b_{adm,can,cfg,conv,gen,hist,inh,ipc,lock,measurement_harness,mem,norm,off,out,
  outcome,p5,pkg,prefill,priv,prompt,rdy,rec,reg,res,s2,sem,wire}_001.py`: approved replacement
  coverage. Existing shared M1/M2/M4A/Foundation files remain in the retained selector.

## Portable Test ID mapping

| Test ID | Principal implementation / tests |
| :--- | :--- |
| `M4B-NORM-001` | projector/reasoner; `test_m4b_norm_001.py` |
| `M4B-PROMPT-001` | prompt/profile/lock; `test_m4b_prompt_001.py` |
| `M4B-SEM-001` | semantic parser/reasoner; `test_m4b_sem_001.py` |
| `M4B-S2-001` | incremental safe text and terminal parser; `test_m4b_s2_001.py` |
| `M4B-ADM-001` | MEASURE/discard/grant/privacy; `test_m4b_adm_001.py` |
| `M4B-PREFILL-001` | fresh prefill/context tier; `test_m4b_prefill_001.py` |
| `M4B-OUTCOME-001` | policy/speech/route matrix; `test_m4b_outcome_001.py` |
| `M4B-CONV-001` | Conversation/revision/replacement; `test_m4b_conv_001.py` |
| `M4B-MEM-001` | resource decisions/series; `test_m4b_mem_001.py` |
| `M4B-REC-001` | SM-authorized same-key recovery; `test_m4b_rec_001.py` |
| `M4B-WIRE-001` | v3 wire/order/proofs/PGID; `test_m4b_wire_001.py` |
| `M4B-PRIV-001` | retention/observability/output scans; `test_m4b_priv_001.py` |
| `M4B-REG-001` | immutable/affected/catalog guards; `test_m4b_reg_001.py` |

## Final Developer verification

All commands used `PYTHONPATH=src:.`, strict markers/config, `pytest-timeout`, per-test timeout
`120 s`, outer bounded runners and JUnit xUnit1. Evidence is diagnostic and not candidate evidence.

### Raspberry Pi 5 / Linux aarch64 / CPython 3.13.5

Target: authorized Raspberry Pi 5 Model B Rev 1.1, 4 GiB, Debian 13.2, kernel
`6.12.47+rpt-rpi-2712`; observed before final runs: `38.4 C`, `throttled=0x0`.

- Final Revised portable catalog: **1005 collected, 1005 passed, 0 failed/error/skipped**,
  33.20 s. JUnit: `${PI_RUN}/evidence/portable-pi-revised.xml`, with Developer copy at
  `${DEV_RUN}/evidence/pi/portable-pi-revised.xml`, SHA-256
  `f50763daeab27d58399f6c168f38421ac15d6808dfa0d2b75711988affd8d6fe`.
- Full repository excluding 29 explicitly `rpi`-marked hardware rows: **1557 passed,
  0 failed/error/skipped, 29 deselected**, 54.85 s. JUnit:
  `${PI_RUN}/evidence/full-non-rpi.xml`, SHA-256
  `65251bd288c7bdecb6a0190cbe3fc62bbd4c0fd88094e3001485b6c6be83d406`.
- `python -m compileall -q src scripts tests`: exit 0.
- `git diff --check`: exit 0.

### Immutable Foundation evidence

- Baseline count: **99**; retained: **99**; missing: **0**; skipped: **0**.
- Baseline and collected list SHA-256:
  `fd5a9eb2d9943e894fc2a4e043146b1a85874f7eafcd88996686188d5477813f`.
- Missing-list SHA-256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- The portable JUnit `G02` testcase carries the same six inventory properties.

### macOS arm64 diagnostics

- CPython 3.11.16, 3.12.14 and 3.13.15 each: **1005 collected, 997 passed,
  8 failed, 0 error/skipped**. All eight are the same Accepted M4A Darwin process-group nodes
  (seven direct nodes plus `M4B-REG-001/G05` aggregation); no M4B production node failed.
- CPython 3.13.15 full non-hardware suite: **1547 passed, 10 failed, 29 deselected**.
  The two additional failures are the same M4A ASR supervisor cleanup boundary.
- Exact starting-SHA archive control over the three direct M4A files: **40 passed, 9 failed** with
  the same nine direct nodes. Evidence:
  `${DEV_RUN}/evidence/starting-sha-m4a-darwin.xml`.
- Current diagnostics:
  `${DEV_RUN}/evidence/mac{311,312,313}-final.{xml,json,stdout}` and
  `${DEV_RUN}/evidence/mac-full-final.xml`.

This is reported as a pre-existing Darwin M4A platform defect, not hidden by skip/xfail and not
converted into M4B PASS. The required Linux Python 3.13 subprocess cell is green on the Pi.

## Pending target and human rows

`PM`, product acceptance and human semantic/audio rows remain **Pending**, with no PASS claim.
The Pi currently has no approved clean candidate checkout, locked LiteRT-LM model/runtime,
private audio-only config, artifact lock matching those files, empty `0700` output directory or
Designer+Tester authorization JSON bound to the exact candidate/profile/harness/target tuple.
The Developer harness correctly rejects that incomplete context.

The next legal sequence is USER-approved commit/candidate preparation, independent Tester portable
verification, dual-role PM authorization, then native measurement/human execution. Temporary legacy
documentation remains until the product §12 portable-and-Pi cutover gate is actually satisfied.
