---
requestor: Designer
owner: Developer
status: Revised
severity: Blocking
---

# CR_M4B_II — replacement cognition/product rewrite

- Date: 2026-09-12
- Gate: `M4B-DEVELOPMENT-REWRITE`
- Activation: **Active after this work package and its linked authority are present in the Developer checkout**
- Candidate status: none; this is implementation work, not product acceptance

## Authority and entry

Developer first reads [`status/current.md`](../status/current.md), `status/development.md`, this work package,
[`ch_m4b_llm_production.md`](../implement/ch_m4b_llm_production.md), and the approved
[`test_spec_M4B.md`](../test_spec/test_spec_M4B.md). Read only the directly cited M4B sections of
[`protocol.md`](../protocol.md) §4, [`model_spec.md`](../model_spec.md) §6,
[`ch02b_workers.md`](../implement/ch02b_workers.md) §3 and [`ch10_config.md`](../implement/ch10_config.md) §6.

Resolved review provenance is [`AR_impl_M4B_IV`](history/AR_impl_M4B_IV.md),
[`IR_review_M4B_III`](history/IR_review_M4B_III.md) and
[`TR_spec_M4B_VI`](history/TR_spec_M4B_VI.md), plus the focused ticket-disposal correction
[`IR_dev_M4B_IV`](history/IR_dev_M4B_IV.md) / [`TR_spec_M4B_VII`](history/TR_spec_M4B_VII.md). Do not load retired
M4B design, test specs or candidate behavior as implementation authority.

Before editing code, replace `status/development.md` with the exact affected paths, symbols, mapped Test IDs,
estimates and bounded verification commands. Record the 40-character starting SHA. If the work-package authority is
not committed in that checkout, stop and report the missing handoff instead of implementing against an unstated
worktree delta.

## Required implementation

### WP-01 — Profile, prompt and config

- Implement `core-m4b-cognition-001`, exact V2D2 bytes/counts/hashes, grammar identity and field-by-field artifact
  attestation. No prompt/YAML personality override, fallback endpoint or system-site dependency.
- Implement strict listen-only composition and reject all legacy profile/recycle keys. Measurement and release
  profiles remain separate; do not invent memory thresholds.
- Cover `M4B-PROMPT-001`, `M4B-SEM-001`, relevant `M4B-NORM-001` and config rows.

### WP-02 — Child protocol and adapter

- Replace the legacy child wire with `snowboard.llm/3` READY/OPEN/MEASURE/DISCARD_TICKET/GENERATE/SAFE_TEXT/
  RESULT/REQUEST_FAILED/CANCEL/CLOSE/SHUTDOWN semantics, exact identities and bounded framing.
- Implement non-mutating MEASURE, exact acknowledged ticket disposal, one-use ticket binding, GENERATE-only
  mutation, state/order rejection and terminal/join/cleanup/Engine-usable proofs. Preserve one Conversation across
  normal turns. Resolved `IR_dev_M4B_IV` and `TR_spec_M4B_VII` authorize this exact disposal path; no implicit
  supersession or CLOSE workaround is allowed.
- Own the dedicated PID=PGID lifecycle, descendants, TERM/KILL/waitpid proof and fully attested new child after
  recovery. Cover `M4B-ADM-001`, `M4B-PREFILL-001`, `M4B-S2-001`, `M4B-WIRE-001` and `M4B-CONV-001`.

### WP-03 — Reasoner product policy

- Implement exact projection/normalization, input/context/memory admission, constrained semantic validation and the
  complete §6 outcome matrix. One turn performs at most one generation and publishes exactly one normal Fact.
- Preserve application/model speech ownership, final-speak-then-rest, KEEP/REPLACE/END, no replay and repeated R2
  without count escalation. Unsafe contract/protocol/backend paths remain E1.
- Cover `M4B-NORM-001`, `M4B-SEM-001`, `M4B-OUTCOME-001`, `M4B-MEM-001` and `M4B-PRIV-001`.

### WP-04 — SM-authorized planned recovery

- Adapter atomically marks `RECYCLE_PENDING`; Conversation cleanup proof alone must never schedule recovery.
- Implement a narrow private SM authorization seam, or an equivalent internal control with the same observable
  contract, inside the existing post-close convergence phase. Do not add a public SM state, Event, Fact or
  `LLMResponse` field; do not expose RM to Reasoner or infer capacity from spoken text.
- Adapter/composition invokes only the exact same-key schedule/wait seam after authorization. RM owns rebuild,
  timeout and barrier; SM retains session tracking and blocks wake/IDLE until READY. Cover every `M4B-REC-001` row.
- Supporting private changes in composition/SM/RM surfaces are allowed only when directly required by these approved
  assertions and must be inventoried before edit. Any public-contract change requires `IR_dev`, not improvisation.

### WP-05 — Observability, privacy and tooling

- Produce the separate prompt, runtime/context, memory and one-clock timing schemas without private content or
  audible-onset/latency claims. Remove workdirs/content and supervise recovery failure even without a next request.
- Replace `scripts/m4b_*` and `requirements/m4b/` surfaces needed for deterministic portable tests, artifact locks,
  measurement-only capture and later release-profile execution. Tooling must fail closed and remain offline.
- Pi measurement/human execution stays Pending until a clean exact-SHA candidate, target access and the later Tester
  execution gate. Developer may implement the specified harness/card schemas but may not claim Pi evidence.

### WP-06 — Tests, regression and cutover

- Implement every portable Test ID/case in `test_spec_M4B.md`; table-driven grouping is allowed only with preserved
  Test ID/case/assertion evidence. Use explicit barriers and bounded waits, never correctness sleeps.
- Retain all 99 immutable Foundation nodes, strict zero-skip behavior and affected M1/M2/M4A shared-path coverage.
  No delete/rename/skip/xfail/assertion weakening may create a green result.
- Replace current M4B production/test inventory in place. Do not restore legacy action-envelope, per-turn fresh
  Conversation, fake prewarm, fixed `8/48/768`, forced session-count or response-time ceiling behavior.
- Temporary legacy documentation inventory is removed only at the final verified cutover specified by product §12,
  not during an incomplete portable implementation.

## Candidate and verification boundary

Developer must run the complete portable catalog with the declared Python/platform matrix feasible in the working
environment, the immutable 99-node comparison and strict JUnit gate, affected shared-path regressions, full repository
suite, compile/static checks and privacy/diff checks. Missing native/Pi capability is reported separately and cannot
be converted to portable PASS or product acceptance.

Before returning the work package, update this review to `Revised` with:

1. changed paths and symbols mapped to WP-01–06 and every portable Test ID;
2. exact bounded commands, collected node IDs, exit status, pass/fail/error/skip/xfail/xpass counts and evidence
   locators;
3. immutable baseline count, retained count, missing count and list digests;
4. explicit inventory of Pending Pi/human rows and any missing target/profile input;
5. removal/replacement inventory for legacy production/tests, with no acceptance claim;
6. any design/API blocker as a separate `IR_dev` with the conflicting clauses and minimum required decision.

Do not commit, push, create a candidate or alter design/test authority without explicit USER authorization. After
Developer returns `Revised`, Tester independently verifies the portable candidate before Designer final alignment.

## Developer disposition — 2026-09-12

WP-01–06 are implemented and returned **Revised** for independent Tester verification. This is
not product acceptance: there is no commit, pushed candidate, native PM result or human PASS.

### Changed paths and portable mapping

- WP-01: `src/sbd/cognition/{prompt_builder,semantic,factory}.py`,
  `src/sbd/cognition/litert_lm/lock.py`, `src/sbd/core/config/{loader,models,validate}.py`,
  `config.example.yaml`, `requirements/m4b/*`, and
  `scripts/{m4b_inheritance,m4b_llm_product}.py`. Covers `M4B-NORM-001`, `M4B-PROMPT-001`,
  `M4B-SEM-001` and config/artifact portions of `M4B-PRIV-001`.
- WP-02: `src/sbd/cognition/{llm,llm_child_protocol}.py`,
  `src/sbd/cognition/litert_lm/{adapter,worker,measurement}.py` and
  `tests/fakes/m4b_llm_child.py`. Covers `M4B-S2-001`, `M4B-ADM-001`,
  `M4B-PREFILL-001`, `M4B-CONV-001` and `M4B-WIRE-001`, including A01–A13 and W01–W12.
- WP-03: `src/sbd/cognition/reasoner.py`, `src/sbd/core/state_manager/{manager,notices}.py`.
  Covers `M4B-NORM-001`, `M4B-SEM-001`, `M4B-OUTCOME-001`, `M4B-CONV-001`,
  `M4B-MEM-001` and `M4B-PRIV-001`.
- WP-04: `src/sbd/core/{m2_composition,_m4b_resource_binding}.py` and
  `src/sbd/action/rest/action.py`. Covers `M4B-REC-001`, resource ownership and stale Rest
  completion barriers.
- WP-05: `src/sbd/cognition/{observability.py,litert_lm/resource.py}`,
  `src/sbd/perception/listen/listener.py`, `src/sbd/action/speak/speaker.py`,
  `src/sbd/core/audio/alsa/output.py`, and
  `scripts/{m4b_target_metrics,m4b_measurement}.py`. Covers `M4B-MEM-001`,
  `M4B-PRIV-001`, target safety and observation schemas.
- WP-06: `scripts/candidate_gate.py`, `tests/m4b_portable_suite.txt`,
  `tests/m4b_target_cases.py`, all current `tests/test_m4b_*` replacements/additions and retained
  shared M1/M2/M4A/Foundation selectors. Covers `M4B-REG-001` and completes all 13 portable IDs.

The exact symbol/path and one-row-per-ID inventory is in
[`status/development.md`](../status/development.md). Legacy M4B fresh-conversation, action-envelope,
fake-prewarm, fixed-threshold, forced-session-count and response-ceiling assertions were replaced
in place. Immutable Foundation and Accepted shared tests were retained; temporary legacy
documentation was not removed because the Pi cutover gate is not complete.

### Verification evidence

On the authorized Pi 5 4 GB target (Debian 13.2 aarch64, CPython 3.13.5), using strict pytest config,
xUnit1 JUnit and a 120-second per-test bound:

- final Revised portable catalog: **1005 collected / 1005 passed / 0 failed / 0 error /
  0 skipped / 0 xfailed / 0 xpassed**, exit 0, 33.20 s;
- full repository with 29 explicitly hardware-marked rows deselected: **1557 passed / 0 failed /
  0 error / 0 skipped / 29 deselected**, exit 0, 54.85 s;
- `python -m compileall -q src scripts tests` and `git diff --check`: exit 0.

Pi evidence remains at `${PI_RUN}/evidence/`; copied Developer diagnostics are under
`${DEV_RUN}/evidence/pi/`. The final Revised portable JUnit is
`portable-pi-revised.xml`; its and the full JUnit SHA-256 values are respectively
`f50763daeab27d58399f6c168f38421ac15d6808dfa0d2b75711988affd8d6fe`
and `65251bd288c7bdecb6a0190cbe3fc62bbd4c0fd88094e3001485b6c6be83d406`.

Immutable evidence is **99 baseline / 99 retained / 0 missing / 0 skipped**. Baseline and
collected node-list SHA-256 are both
`fd5a9eb2d9943e894fc2a4e043146b1a85874f7eafcd88996686188d5477813f`; the empty missing-list
digest is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

macOS arm64 diagnostics on CPython 3.11.16, 3.12.14 and 3.13.15 each collected 1005 and produced
**997 passed / 8 failed / 0 error / 0 skipped**. The failures are seven Accepted M4A Darwin
process-group nodes plus the `M4B-REG-001/G05` aggregation. The 3.13 full non-hardware suite was
**1547 passed / 10 failed / 29 deselected**; the two additional failures are the same M4A ASR
supervisor cleanup boundary. An exact starting-SHA archive control produced **40 passed / 9 failed**
for the nine direct M4A nodes, proving the same pre-existing defect. It remains visible and is not
converted into M4B PASS. Current and control JUnit/JSON/stdout are under
`${DEV_RUN}/evidence/`.

### Pending target/human work and blockers

Native `PM`, product gate cards and human semantic/audio rows remain **Pending**. Missing inputs are
a clean exact-SHA candidate checkout, locked LiteRT-LM runtime/model files, matching artifact lock,
private audio-only config, empty mode-`0700` output directory, and Designer+Tester authorization
bound to the exact candidate/profile/harness/target tuple. The measurement entry rejects the
current incomplete context and cannot generate a release/human PASS.

There is no new design/API blocker. The sole blocking protocol gap was resolved by
`IR_dev_M4B_IV` / `TR_spec_M4B_VII`; implementation uses the authorized explicit discard command
and acknowledgement, never implicit supersession or a `CLOSE` workaround.

## Tester diagnostic disposition — 2026-09-12

Disposition: **Rejected** for exact provisional candidate
`9e005e48fe1582c901fcba3eb152747c92c43890` because the candidate gate admits false and incomplete
portable PASS evidence. Native `PM`/`PR`/`PH`, product cards and human rows remain **Pending** and
were not executed.

Tester run `tester-m4b-20260912-a1` used a detached clean checkout at the exact candidate SHA on
macOS 15.5 arm64 and the candidate-owned `scripts/candidate_gate.py portable --suite tests
--timeout-seconds 480` command. The independent results are:

| Runtime | Passed | Failed | Skipped | XFailed | Deselected | Status |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| CPython 3.11.16 | 1546 | 11 | 0 | 0 | 29 | Fail |
| CPython 3.12.14 | 1547 | 10 | 0 | 0 | 29 | Fail |
| CPython 3.13.15 | 1547 | 10 | 0 | 0 | 29 | Fail |

The macOS diagnostic matrix command exited 1 with `Python 3.11 portable result is not Pass`; no
PASS matrix index was produced. Diagnostic evidence is under
`/private/tmp/m4b-tester-YN5xRw/evidence/portable/tester-m4b-20260912-a1/`; each `python-3.*`
directory contains `result.json`, `junit.xml` and raw stdout/stderr. Result/JUnit SHA-256 pairs are
`33669803cbde07f4c4ad8686d6a019e32db838082a7c4665e507d28f6e7bbd8d` /
`0c73effd4eae119e73492e1f4d523f772035e37608ee96fe659669cfa07232d3` (3.11),
`6ffe01af1ec01a030503cea26ab3d2778b5204be48507391389fd704e9ff0743` /
`e6f204c8dc22f9f49661225ae9d5450e49d0f790991364cf6fc9c3ca19810f55` (3.12), and
`88ec90450e741c00deb6fcb66d28c48862e44954fea0169ef10d8098daa59549` /
`2bb731b1813e2307e4d6f7c7bb58d1febe38c60f75659b3ac3befe97e5f501f0` (3.13).
`matrix-failure.json` records the aggregate rejection.

Positive checks do not establish Linux PASS: immutable Foundation comparison is **99 baseline /
99 retained / 0 missing**, with baseline/collected digest
`fd5a9eb2d9943e894fc2a4e043146b1a85874f7eafcd88996686188d5477813f` and empty missing digest
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; `compileall`,
`git diff --check`, protected-input cleanliness and exact HEAD checks exited 0.

### B1 — Blocking: portable runner and matrix admit false/incomplete PASS evidence

- **Basis:** `test_spec_M4B.md` §2.1 makes any XPASS a Fail, §2.4 requires exact candidate/profile/
  matrix identity and per-Test-ID evidence, and `M4B-REG-001` requires the complete immutable and
  affected catalog. `candidate-process.md` requires zero Fail/Skip/XFail on the formal supported
  matrix. A caller-selected trivial suite cannot substitute for those gates.
- **Location:** `scripts/candidate_gate.py` `suite_counts()`, `passed()`, `portable()`,
  `validate_version_result()` and `matrix()`. `m4b_collection_audit()`, `m4b_source_violations()`,
  `m4b_junit_audit()` and `m4b_catalog_paths()` are test helpers but are not enforced by the portable
  runner or matrix. `tests/test_candidate_gate.py` constructs minimal version results without suite,
  platform, evidence digest or Test-ID identity and treats them as valid matrix inputs.
- **XPASS reproduction:** an external one-node probe marked `pytest.mark.xfail` and containing a
  passing assertion produced pytest summary `1 xpassed`, but the candidate runner exited 0 and wrote
  `status="Pass"`, `passed=1`, `failed=0`, `skipped=0`, `xfailed=0`. Evidence is
  `/private/tmp/m4b-tester-YN5xRw/evidence/xpass-probe/`; result/JUnit SHA-256 are
  `637cdf6176f2e89ad9ed288d7e166ddc37cb72652af1ae9180367815b15cfc24` and
  `666a264b6582fa9d10b9bd8152bd38a48c15ede45dd24b538cd4a7c5a200cf99`.
- **Incomplete-suite reproduction:** the runner accepted the external absolute selector
  `/private/tmp/m4b-tester-YN5xRw/trivial_probe.py`, containing only `assert 1 == 1`, for each of
  Python 3.11/3.12/3.13. The matrix command then exited 0 and produced
  `/private/tmp/m4b-tester-YN5xRw/evidence/trivial-matrix/matrix-index.json` with `status="Pass"`.
  Its SHA-256 is `4c46f851a2f7bbde2be7c41b8f9432ecd9d29e044afb66ac07dae92e0c7825de`.
  The accepted records were generated on macOS even though the USER-adjusted formal profile now
  requires Linux; `validate_version_result()` does not validate platform or canonical suite.
- **Expected / actual / impact:** only the complete candidate-owned Linux suite, all required Test
  IDs and zero fail/error/skip/xfail/xpass may yield PASS. Actual code trusts caller-selected test
  paths and incomplete result JSON, omits XPASS from counts, and creates a PASS matrix from three
  trivial nodes. The matrix can therefore authorize later preflight without proving the product.
- **Preferred correction:** bind portable execution and aggregation to the tracked canonical suite;
  reject absolute/out-of-repo/arbitrary selectors; record and validate exact Linux/platform/Python,
  suite/catalog digest, collection/JUnit identity, per-Test-ID evidence and zero XPASS. Integrate the
  existing M4B audit helpers into the formal path rather than relying on tests that can themselves be
  omitted. Add negative tests for both reproductions without weakening protected tests.
- **Minimum verification:** both probes must be rejected; an XPASS must make the runner and matrix
  Fail; incomplete/mixed platform, suite, catalog, identity or evidence records must be rejected;
  then rerun the immutable baseline and the complete Linux CPython 3.11/3.12/3.13 portable matrix
  with zero Fail/Error/Skip/XFail/XPASS.

### D1 — Diagnostic: Darwin process-group exit proof fails on macOS

- **Basis at execution time:** `M4B-REG-001/G05` selected the affected M4A process-group cleanup
  boundary. USER subsequently classified macOS as diagnostic-only for this candidate.
- **Location:** `src/sbd/adaptor/framed_child.py` `_live_process_group_members()` and
  `_wait_process_group_exit()`; direct failures are two `test_m4a_asr_001` rows, six
  `test_m4a_ipc_001` rows, `test_m4a_priv_001`, and aggregate `test_m4b_reg_001::test_G05_*`.
- **Reproduction:** all three formal minor runs fail the same ten rows. A bounded standalone CPython
  3.13 run of `test_m4a_ipc_001_ready_identity_idempotent_lifecycle_and_cleanup` also fails with
  `AudioProtocolError: child process group exit could not be proven`. The same node fails at starting
  SHA `54c506713082b1ea95cfa331f08b7124dcfa0316`, so this is pre-existing.
- **Expected / actual / impact:** a clean shutdown must prove root and descendant exit and remove its
  workdir; on Darwin, absence of `/proc` returns `{pgid}` indefinitely, so TERM/KILL both time out.
  This explains the macOS diagnostic failure but does not reject the candidate after USER's runtime
  disposition. No Developer correction is requested for this row.

### D2 — Diagnostic: macOS CPython 3.11 camera cancellation is not propagated

- **Basis at execution time:** the full repository diagnostic suite selected this row. USER
  subsequently classified macOS as diagnostic-only for this candidate.
- **Location:** `scripts/hw_diag/hw_diag.py` `_bounded()` / `check_camera()` and
  `tests/test_pm_025_hw_diag.py::test_pm_025_camera_cancellation_propagates_after_cleanup`.
- **Reproduction:** the 3.11 formal run and a bounded standalone rerun both fail after about ten
  seconds with `cancellation must propagate`; 3.12/3.13 pass this row. The same bounded 3.11 node
  fails at starting SHA `54c506713082b1ea95cfa331f08b7124dcfa0316`, so it is also pre-existing.
- **Expected / actual / impact:** cancelling during blocked capture must clean the camera and raise
  `CancelledError`; actual execution returns normally after the operation timeout. This explains
  the eleventh macOS 3.11 diagnostic failure. No Developer correction is requested for this row.

### USER runtime clarification and remaining gate

USER directed on 2026-09-12 that these macOS results have no acceptance significance and may be
excluded. They remain visible as diagnostics; no committed skip/xfail or candidate change is requested.
The required independent result remains Linux CPython 3.11/3.12/3.13 with zero
Fail/Error/Skip/XFail/XPASS, but B1 must be corrected first because the current runner cannot prove that result.
This workstation has no Linux/container runner, and the available GitHub CLI has no authenticated host.
Developer's earlier Pi/Linux diagnostics cannot be relabeled as Tester evidence. Because B1 changes protected
runner/tests, correction requires an append-only fix commit and a new exact candidate SHA.

## Developer B1 correction disposition — 2026-09-12

Disposition: **Revised**. B1 is corrected in the working tree; no replacement commit, candidate,
portable PASS, PM, PR or PH claim is made. The rejected SHA
`9e005e48fe1582c901fcba3eb152747c92c43890` remains immutable.

### Corrected implementation and coverage

- `scripts/candidate_gate.py` now treats failure, error, skip, XFail and XPASS as distinct forbidden
  outcomes. A real XPASS probe exits nonzero and records `status=Fail`, `xpassed=1`.
- Formal M4B portable execution accepts only the exact tracked
  `tests/m4b_portable_suite.txt`; absolute/repo-external paths, `tests`, and arbitrary repository
  files are rejected before execution. The canonical manifest, product profile, immutable baseline
  and every selected test path must be candidate-tracked.
- Each run now binds Linux x86_64/aarch64, CPython minor/full version, exact profile ID/digest,
  catalog paths/digest, independently collected node IDs/digest, source audit, sanitized JUnit
  digest, monotonic bounds, raw-log locators, exact Foundation G02 properties and node/digest
  evidence for all 13 current portable Test IDs.
- Matrix and later preflight validation reopen the evidence below each version result, reject
  traversal/symlink/missing locators, recompute collection/JUnit/source/Foundation/Test-ID identity,
  require zero Fail/Error/Skip/XFail/XPASS and bind the matrix index to all three result digests plus
  the current profile/catalog identity.
- `tests/test_candidate_gate.py` adds executable canonical-run coverage and negative cases for the
  two B1 reproductions plus mixed platform, suite, catalog, profile, Test-ID, JUnit and XPASS matrix
  records. D1/D2 and Tester-owned macOS diagnostic-only disposition are unchanged.

### Bounded Developer verification

- CPython 3.11.16: `tests/test_candidate_gate.py` — **78 passed**, exit 0, 12.88 s.
- CPython 3.12.14: `tests/test_candidate_gate.py` — **78 passed**, exit 0, 13.57 s.
- CPython 3.13.15: `tests/test_candidate_gate.py` — **78 passed**, exit 0, 13.19 s.
- CPython 3.13.15: `tests/test_m4b_reg_001.py -k 'not G05'` — **15 passed /
  1 USER-disposed Darwin diagnostic deselected**, exit 0, 17.68 s.
- Direct current-candidate authority audit: profile
  `core-m4b-cognition-001` / `be9005b5426173243ab1306dc24fb969f1371ff86615286ac1405714a98b49f1`,
  31 canonical selectors, catalog SHA-256
  `bcd92cc2019494f3c854337b761585b79cbddd0f0a7d6b381ff8c35f21c2e001`, source-audit SHA-256
  `bd68b36c38eb53c58226a9aee8f8527c0fe1bb077f22704622930d688dbb2ccf`, exit 0.

All pytest commands used a 180-second outer process alarm and `--timeout=120`; no correctness sleep
or acceptance threshold was introduced. Final compile and diff checks are recorded in
`status/development.md`.

### Required independent re-verification

Because `scripts/candidate_gate.py` and `tests/test_candidate_gate.py` are protected inputs, the
previous candidate and all prior matrix evidence are invalidated. After an authorized append-only
commit creates a new exact SHA, Tester must independently run the complete canonical Linux CPython
3.11/3.12/3.13 matrix and confirm both B1 probes reject. PM/PR/PH remain Pending until that portable
verification and subsequent Designer target-gate transition are complete.

## Tester Pi collection finding B2 — 2026-09-13

Disposition at exact candidate `1eefd97dd9866f804d07be6aacddb6948d05b6e1`: **Rejected**.
Tester executed the formal candidate-owned portable runner on Pi with pytest 9.1.1. The project
already supplies `addopts = "-ra -q"`; `_m4b_collect_nodes` added another `-q`, so the effective
`-qq` collection output contained per-file counts instead of `path::node` identities. The run
failed closed with `M4B_COLLECTION_INVALID` before the portable suite executed. Tester confirmed
that adding `-o addopts=` restores node-ID output. No product-runtime, PM, PR or PH result was
produced.

## Developer B2 correction disposition — 2026-09-13

Disposition: **Revised**. `_m4b_collect_nodes` now clears repository `addopts` for its collection
subprocess and then applies exactly one runner-owned `-q`. Canonical selectors, `not rpi`, process
timeout, duplicate detection and missing-node rejection are unchanged.

`tests/test_candidate_gate.py` now constructs its candidate fixture with pytest
`addopts='-q'` in `pyproject.toml`. The executable M4B canonical-run regression verifies that the
collection evidence contains exactly 13 unique `tests/...::...` node IDs and that the bound result
passes all 13 Test-ID and 99-node Foundation evidence checks. This test would reproduce B2 as
`M4B_COLLECTION_INVALID` without the runner override.

Bounded Developer results using CPython 3.13.15 and pytest 9.1.1:

- focused canonical collection regression: **1 passed**, exit 0, 0.75 s;
- complete `tests/test_candidate_gate.py`: **78 passed**, exit 0, 13.21 s;
- `python -m compileall -q scripts/candidate_gate.py tests/test_candidate_gate.py`: exit 0;
- `git diff --check`: exit 0.

No commit or push was made. Because both changed files are protected candidate inputs, exact SHA
`1eefd97dd9866f804d07be6aacddb6948d05b6e1` remains immutable and rejected. After an authorized
append-only commit creates a new exact candidate, Tester must rerun the complete formal Linux
CPython 3.11/3.12/3.13 canonical matrix from fresh evidence roots. PM/PR/PH remain Pending.
