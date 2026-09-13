# Current development status

## USER-directed PM/PR/PH runner correction — 2026-09-13

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
