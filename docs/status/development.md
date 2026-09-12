# Current development status

- Updated: 2026-09-12
- Owner: Senior Developer / integration owner
- Scope: `CR_M4B_II` B1, fail-closed portable runner and matrix evidence
- Starting SHA: `9e005e48fe1582c901fcba3eb152747c92c43890`
- Status: **B1 correction complete; Revised for new append-only candidate verification**
- Next owner: Tester, after USER-authorized append-only commit creates a new exact candidate
- Candidate: rejected provisional SHA `9e005e48fe1582c901fcba3eb152747c92c43890`;
  no replacement commit, push, Pi measurement PASS or human acceptance is claimed

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
