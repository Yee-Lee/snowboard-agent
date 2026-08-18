---
requestor: "Designer"
owner: "Developer"
status: "Resolved"
---

# CR_M4_I — PM-OUT-260817-014 Candidate Gate Reform Review

## Review disposition

**RESOLVED — all seven findings are closed; implementation is ready for a commit proposal.**

This is the Designer review of the uncommitted M4 candidate-gate reform for
`PM-OUT-260817-014-local-hardware-test-gate-reform`. The rejection and revision history is retained
below. The final focused correction closes the last false-green aggregate identity path. This
review resolution does not itself authorize a commit; the complete proposed commit message and
file list still require explicit USER approval.

Reviewed implementation scope:

- `pyproject.toml`
- `.github/workflows/candidate-portable.yml`
- `scripts/candidate_gate.py`
- `tests/test_candidate_gate.py`
- `docs/reviews/dev_progress_M4.md`

Authoritative basis:

- `docs/outsource/pm_handoff/PM-OUT-260817-014-local-hardware-test-gate-reform/brief.md`
- `docs/outsource/responses/OUT-PROCESS-2026-001.md`
- `docs/runbooks/candidate_hardware_gate.md`
- `docs/test_spec.md` §2.4
- `docs/roles/workflow.md` §4 and §4.1

## Blocking findings

### CR-M4-014-001 — Portable matrix evidence is not fail-closed by identity

- **Contract basis**: `docs/test_spec.md` §2.4 items 1–3; runbook §4 and §7 require every
  per-version result and matrix index to bind the same external candidate SHA, portable run ID,
  Python implementation/minor, platform, command, timeout, dependency identity and counts.
- **Evidence / minimal reproduction**: `verify_matrix()` checks status, candidate SHA and counts,
  but does not check the referenced result's `run_id`, `python_minor`, platform or dependency
  checksum. The positive preflight fixture in `tests/test_candidate_gate.py:65-84` deliberately
  creates all three version results without `run_id` or `python_minor`; preflight still exits `0`.
- **Expected / actual**: incomplete or mixed version identity must fail before target work; it is
  currently accepted as a PASS matrix.
- **Impact**: results from a different portable attempt or runtime can authorize the Pi preflight.
- **Recommended direction / minimum acceptance**: validate every required identity field against
  the matrix key/index and reject missing fields. Add negative coverage for missing/wrong run ID,
  Python minor, platform and dependency checksum; every case must exit non-zero and retain a FAIL
  bundle without creating `preflight.json`.

**Developer response — Revised:** `scripts/candidate_gate.py` now validates each result's portable
run ID, Python minor and CPython version, platform, argv, bounded timeout, dependency checksum,
raw logs and exact counts. The matrix stores and revalidates the same per-version identities and a
single dependency checksum. Covered by
`test_matrix_identity_is_fail_closed` and
`test_portable_matrix_index_requires_complete_same_candidate_identity`.

### CR-M4-014-002 — Manual observation can be prepared before the formal card starts

- **Contract basis**: runbook §6 and `docs/test_spec.md` §2.4 item 6 require the formal card to
  start and publish its current-run READY nonce before an operator can submit observation.
- **Evidence / minimal reproduction**: `accept()` validates an already-existing READY record and
  observation before calling `execute_suite()`. A READY/observation pair timestamped five minutes
  before the `accept` invocation is accepted and the command exits `0`.
- **Expected / actual**: only an observation created after the active card's READY handshake may
  pass; the current implementation proves only ordering between two pre-created JSON files.
- **Impact**: a stale or prefilled human PASS can be attached to a later automated run.
- **Recommended direction / minimum acceptance**: make the current acceptance execution own the
  card start and nonce, wait with a bounded timeout for an independently recorded observation, and
  reject records created before card start. Add prefilled, stale, wrong-nonce and missing-observation
  regressions that cannot create a PASS manifest.

**Developer response — Revised:** `accept` now atomically starts the acceptance attempt, creates
the current card's READY record and random nonce inside `cards/`, then performs a monotonic bounded
wait for an independently written record inside `manual/`. Prefilled directories/files, stale
timestamps, wrong nonce, missing observations and record-command failure all fail closed. Covered
by `test_dry_manual_requires_current_card_handshake`.

### CR-M4-014-003 — An acceptance run ID can be resumed and overwritten

- **Contract basis**: workflow §4 step 6, `docs/test_spec.md` §2.4 item 4 and runbook §5 require a
  complete acceptance-first run with a unique, non-reusable run ID. A failed or interrupted run
  must restart under a new run ID.
- **Evidence / minimal reproduction**: after one successful preflight and acceptance, invoking
  `accept` again with the same output/run ID also exits `0`; suite logs, result and manifest are
  rewritten because the accept path does not reserve an attempt or reject an existing result.
- **Expected / actual**: a second invocation must fail before suite execution; the current command
  silently continues the existing acceptance directory.
- **Impact**: evidence from multiple executions can be collapsed into one apparent complete run.
- **Recommended direction / minimum acceptance**: atomically reserve the acceptance attempt before
  the suite and reject any existing attempt/result/manifest marker. A regression must prove the
  second invocation is non-zero and the first run's checksums remain unchanged.

**Developer response — Revised:** `accept-attempt.json` is created with exclusive-create semantics
before READY or suite work. Any existing marker rejects reuse without writing into the prior
bundle. Covered by `test_acceptance_attempt_cannot_be_resumed_or_overwritten`, which hashes the
attempt, result, manifest and suite log before and after the rejected second invocation.

### CR-M4-014-004 — Debug records success without executing the requested node

- **Contract basis**: workflow §4 step 6 and runbook §5 allow debug only after a formal acceptance
  failure, for bounded reruns of a failed card; debug evidence must remain separate and cannot
  repair acceptance.
- **Evidence / minimal reproduction**: `debug()` only reads a JSON object and writes a Diagnostic
  manifest. It never invokes pytest, applies a timeout or writes raw command logs. A fabricated
  `{candidate_sha, status: Fail}` input plus nonexistent node
  `tests/DOES_NOT_EXIST.py::bad` exits `0`.
- **Expected / actual**: debug must consume a valid acceptance FAIL identity and execute the exact
  node; the current implementation treats any string as a successful diagnostic.
- **Impact**: the debug record cannot prove what was run and can be confused with useful failure
  diagnosis.
- **Recommended direction / minimum acceptance**: validate failed evidence mode/run/candidate,
  execute the exact node with a bounded timeout, and record command, exit, counts and raw logs.
  Nonexistent nodes, invalid FAIL inputs and timeout must return non-zero; debug must never emit an
  acceptance PASS manifest.

**Developer response — Revised:** `debug` now requires a distinct
`acceptance/<run-id>/results/result.json` with matching acceptance mode, FAIL status and candidate,
then executes the exact node with `-m rpi` and a bounded timeout. It records counts, argv, exit and
raw logs; only a completed diagnostic gets a debug manifest. Covered by
`test_debug_executes_node_and_rejects_nonexistent_node`,
`test_debug_rejects_fabricated_non_acceptance_failure` and
`test_debug_timeout_is_bounded_and_preserves_logs`.

### CR-M4-014-005 — Protected candidate paths do not cover the controlled runner surface

- **Contract basis**: `docs/test_spec.md` §2.4 item 2 and runbook §2 protect `src/`, `tests/`, all
  acceptance/observation runners, dependency metadata, config contracts and applicable CI.
- **Evidence / minimal reproduction**: `PROTECTED_PATHS` names only two exact script files and one
  exact workflow. An untracked `scripts/run_m4_acceptance.py` is not reported by
  `inspect_repository()` and portable execution still exits `0`.
- **Expected / actual**: adding or modifying a candidate/acceptance runner must revoke the clean
  candidate; the current allowlist misses new controlled scripts and workflows.
- **Impact**: the executed gate surface can differ from the candidate SHA without invalidating it.
- **Recommended direction / minimum acceptance**: protect the complete controlled script/workflow
  scope, or derive and freeze an explicit exhaustive manifest. Regressions must cover untracked and
  modified runner/workflow files and reject them before suite execution.

**Developer response — Revised:** the protected boundary now includes all of `scripts/` and all of
`.github/workflows/`, in addition to production, tests, dependency metadata and config/artifact
contracts. `test_dry_dirty_protects_complete_runner_surface` covers modified and untracked scripts
and workflows before suite execution.

### CR-M4-014-006 — Matrix failure handling can crash instead of producing the required FAIL bundle

- **Contract basis**: runbook §8 requires every dry-run failure to produce non-zero exit, a clear
  FAIL reason and an independent raw log without an acceptance PASS manifest.
- **Evidence / minimal reproduction**: `build_matrix()` writes `matrix-index.json` and then raises
  `GateFailure`; the common handler passes that file path to `write_failure()`, which treats it as a
  directory. A missing Python result therefore emits a traceback/`NotADirectoryError` and no valid
  matrix failure log.
- **Expected / actual**: the original gate reason must be retained in machine-readable evidence;
  failure reporting currently raises a second exception.
- **Impact**: Tester cannot distinguish the intended matrix rejection from runner failure, and the
  required DRY-MATRIX evidence is absent.
- **Recommended direction / minimum acceptance**: give matrix failures a defined evidence directory
  or a file-safe failure writer. Missing, malformed and mixed matrix cases must exit non-zero with
  no traceback, retain a reason/raw log, and never produce a PASS index.

**Developer response — Revised:** failure writing now distinguishes an evidence file from its
directory. Matrix rejection writes a `status=Fail` index plus `matrix-failure.json` and
`logs/matrix.stderr.log`, without a secondary exception. Covered by
`test_matrix_builder_failure_has_machine_readable_bundle` and the matrix identity regressions.

### CR-M4-014-007 — Final evidence does not preserve the preflight and manual identity chain

- **Contract basis**: runbook §7, workflow §4.1 and `docs/test_spec.md` §2.4 item 7 require identity,
  preflight, result, card, manifest and manual observation to reconcile the same SHA/run/mode and
  frozen config/artifact/hardware inputs.
- **Evidence / minimal reproduction**: preflight calculates config, artifact and hardware checksums,
  but `accept()` creates its result/manifest from a new identity object and does not carry those
  checksums, freeze/matrix identity or preflight checksum forward. It records manual/READY paths
  without immutable content checksums.
- **Expected / actual**: final evidence must prove that inputs and observations did not change after
  preflight; the current manifest only points to mutable files.
- **Impact**: post-preflight edits cannot be detected during final reconciliation.
- **Recommended direction / minimum acceptance**: bind the preflight checksum and all frozen input,
  matrix, READY and observation identities/checksums into result/manifest/card evidence. Add a
  mutation regression showing that changing any consumed file after preflight prevents acceptance.

**Developer response — Revised:** preflight now stores immutable path/checksum references for
hardware, config, artifact, freeze manifest, matrix index and all three version results. Acceptance
requires byte-identical identity/preflight records, rehashes every frozen input before starting,
and carries the complete chain plus READY/observation checksums into result and manifest. Covered by
`test_acceptance_binds_preflight_and_manual_evidence_checksums` and
`test_post_preflight_consumed_input_mutation_prevents_acceptance` (hardware, freeze, matrix,
version-result and identity mutations).

## Advisory

- Pinning GitHub Actions by immutable commit SHA would improve supply-chain reproducibility, but the
  current project contract does not make this a submission blocker.
- The local full non-RPi run is incomplete because the environment lacks `samplerate`/`pip`. This
  does not invalidate the focused fast loop, but the future immutable candidate cannot advance
  until CI/Tester supplies the required three-minor matrix with zero Fail/Blocked/Skip/XFail.

## Designer verification

```text
PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py
7 passed

python3 -m py_compile scripts/candidate_gate.py
exit 0

Additional minimum reproductions:
- incomplete per-version identity accepted by preflight: exit 0
- prefilled manual observation accepted: exit 0
- repeated accept on one run ID: first 0, second 0
- nonexistent debug node: exit 0
- untracked acceptance script ignored by protected-path check: exit 0
- missing matrix input: traceback, no valid raw FAIL log
```

These results demonstrate the false-green paths; they are not Tester sign-off.

## Developer revision and resubmission

1. Correct all Blocking findings and their directly affected evidence paths without weakening the
   signed runbook/test contract. If a contract cannot be implemented, open `IR_dev` instead.
2. Reply under each finding with changed paths, behavior and regression node(s), then change this
   review status to `Revised`.
3. Rerun the focused suite, compile check and available non-RPi regression. Preserve the local
   dependency limitation as an environment note rather than claiming a complete full-suite PASS.
4. Do not commit yet. After Designer re-review clears the findings, the complete proposed commit
   message and file list must be shown to USER for explicit approval before a provisional candidate
   commit is created.

## Designer re-review — 2026-08-18

**Disposition: REJECTED — four findings remain open; commit is not authorized.**

The revision materially improves run isolation, checksum binding and failure evidence. The focused
suite increased from 7 to 25 tests and passes. Re-review was restricted to the seven original
findings and their direct evidence paths; no unrelated preference or new product scope was added.

| Finding | Disposition | Re-review result |
| --- | --- | --- |
| `CR-M4-014-001` | **Rejected** | The original run/minor/platform/dependency gaps are fixed, but the positive `version_result()` fixture still omits contract-required branch, protected-path dirty result, start/end time, exit code and suite/Test-ID mapping and is accepted by both matrix build and preflight. The matrix index itself also lacks part of the required execution identity. |
| `CR-M4-014-002` | **Rejected** | READY is now current-run and prefill is rejected, but `accept()` writes READY and waits for operator observation before starting pytest. A card instrumented with a suite-start marker returned acceptance exit `0` while the marker was absent when observation was submitted and appeared only afterward. The observation therefore still cannot prove that the active device/card output was observed. |
| `CR-M4-014-003` | **Pass** | Exclusive `accept-attempt.json` reservation rejects sequential reuse without changing the completed bundle; the regression verifies the prior evidence checksums remain unchanged. |
| `CR-M4-014-004` | **Rejected** | Debug executes the requested node and handles missing nodes/timeouts, but its acceptance-input check is still syntactic. A directly fabricated four-field `{candidate_sha, mode=acceptance, run_id, status=Fail}` file placed under an `acceptance/<run>/results/result.json` shaped path was accepted; a valid RPi node then produced `Diagnostic`, exit `0`. |
| `CR-M4-014-005` | **Pass** | The protected boundary now covers all `scripts/` and `.github/workflows/`; tracked and untracked regressions reject before suite execution. |
| `CR-M4-014-006` | **Pass** | Matrix failure now retains a Fail index, machine-readable failure record and raw stderr without a secondary traceback. |
| `CR-M4-014-007` | **Rejected** | Frozen input mutation is now detected, but the manual observation file itself is accepted without `candidate_sha` or `mode=acceptance`, contrary to the reconciliation contract. Failures after attempt reservation but before suite execution use the minimal `write_acceptance_failure_result()` and lose branch, dirty check, platform/Python and frozen preflight chain. |

### Remaining corrections and minimum acceptance

#### `CR-M4-014-001`

- Validate the complete runbook §4 identity on every version result, including branch, dirty result,
  started/ended timestamps, exit code and suite/Test-ID mapping; ensure the matrix index preserves
  its required aggregate identity.
- Extend the existing table-driven identity regression so removal or mismatch of any required
  identity class prevents both matrix PASS and preflight PASS.

#### `CR-M4-014-002`

- Start the formal suite/card producer before accepting observation. The active test/card must emit
  the READY record only after its device/process stimulus is ready, then wait boundedly for the
  independent operator record before completing.
- Add a regression with an explicit suite-start/producer-ready barrier. It must prove observation
  cannot be submitted or accepted before the active card reaches READY; file timestamp ordering by
  itself is insufficient.

#### `CR-M4-014-004`

- Bind debug to a runner-produced formal acceptance FAIL bundle, not only a four-field JSON object
  and matching directory names. Validate the attempt marker and applicable preflight/result identity
  chain before starting the debug node.
- Add a positive runner-generated FAIL case and a negative path-shaped fabricated FAIL case. The
  current `failed_acceptance()` helper output must be rejected.

#### `CR-M4-014-007`

- Require the manual observation content itself to carry the same full candidate SHA, run ID and
  `mode=acceptance`; preserve its checksum in the final result/manifest as already implemented.
- For every failure after acceptance reservation, preserve the available repository and preflight
  identity chain in `results/result.json`. A manual timeout/prefill/invalid-observation regression
  must verify the FAIL result has candidate/run/mode, branch, dirty result, platform/Python, command,
  frozen input/preflight references, times, exit and raw-log locator.

### Re-review verification

```text
PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py
25 passed in 17.78s

python3 -m py_compile scripts/candidate_gate.py
exit 0

git diff --check
no output

Instrumented manual ordering reproduction:
acceptance exit                         0
suite started before observation       False
suite started after acceptance         True

Path-shaped fabricated FAIL reproduction:
debug exit                             0
debug manifest status                  Diagnostic

PYTHONPATH=src python3 -m pytest -q -m 'not rpi' --maxfail=1
195 passed, 21 deselected, then stopped at the known missing `samplerate==0.2.4` environment dependency
```

Developer should revise only the four Rejected findings and their direct regressions, reply below
this section, and change YAML status to `Revised`. The three Passed findings will not be reopened
unless the next change directly regresses them. Do not commit before the next Designer review and
USER approval of the complete proposed commit message and file list.

## Developer second revision — 2026-08-18

### `CR-M4-014-001` — Revised

`scripts/candidate_gate.py` now requires every portable result to bind branch, clean protected-path
identity, start/end timestamps, zero exit code, suite and non-empty Test-ID mapping in addition to
the previously checked SHA/run/Python/platform/command/timeout/dependency/counts. Matrix build
preserves and preflight revalidates the aggregate branch, platforms, clean state, command, times,
exit and Test-ID mapping. `test_matrix_identity_is_fail_closed` rejects every missing/mismatched
identity in both matrix build and preflight; `test_preflight_rejects_incomplete_matrix_aggregate_identity`
covers aggregate omissions.

**Follow-up correction:** matrix aggregate `command` now must be a non-empty argv whose entries are
non-empty strings. The aggregate identity regression includes the reported `command=[]` mutation
and requires non-zero preflight exit with no `preflight.json`.

### `CR-M4-014-002` — Revised

The acceptance runner now starts pytest before any READY or observation is accepted. The active
pytest card receives a runner-generated nonce through its environment, writes a suite-start record,
then emits READY with its own PID and waits for the independent observation. Runner waits for both
records with monotonic bounded timeouts and terminates the producer on failure. The explicit
`test_manual_observation_follows_active_suite_producer_ready` barrier proves suite start and producer
READY precede observation; stale/prefilled/missing/wrong-nonce cases remain fail-closed.

### `CR-M4-014-004` — Revised

Debug now verifies the runner-created `accept-attempt.json`, its checksum reference, full failed
result identity, raw-log existence, matching preflight checksum and the complete frozen identity
chain before starting a node. `test_debug_rejects_path_shaped_fabricated_acceptance_failure` rejects
the former four-field reproduction. `test_debug_uses_runner_generated_fail_bundle_and_executes_bounded_nodes`
creates a real runner FAIL, proves a valid diagnostic can run, and retains nonexistent-node and
timeout rejection.

### `CR-M4-014-007` — Revised

Manual observation content must now contain the same candidate SHA and `mode=acceptance` as READY,
run and test identity. Every expected failure after attempt reservation is written through the full
failure builder, retaining repository identity, branch/dirty/platform/Python/command/times/exit,
attempt, frozen inputs, preflight and available suite-start/READY/observation checksums plus raw-log
locators. `test_dry_manual_requires_current_card_handshake` validates this full FAIL schema for
prefill, timeout, stale, wrong nonce, record failure and missing observation identity.

### Developer verification

- `tests/test_candidate_gate.py`: all 39 collected cases passed in bounded groups on CPython 3.12.
- `python3 -m py_compile scripts/candidate_gate.py tests/test_candidate_gate.py`: exit 0.
- `.github/workflows/candidate-portable.yml`: YAML parse passed; portable jobs now provide the
  required Test-ID mapping.
- Existing non-RPi result remains `166` core/M1 plus `36` M2 passes and `34` M3 passes / `20`
  deselections, with the known local-only missing `samplerate==0.2.4` failure unchanged.

## Designer second re-review — 2026-08-18

**Disposition: REJECTED — three of the four returned findings pass; `CR-M4-014-001` remains open.**

The second revision correctly closes the active-producer ordering, formal FAIL bundle requirement
for debug, and complete reserved-run failure/manual evidence chain. The portable identity change is
substantially improved, but the matrix aggregate still accepts an empty command argv and therefore
does not fail closed on every required aggregate identity class. Commit remains unauthorized.

| Finding | Disposition | Second re-review result |
| --- | --- | --- |
| `CR-M4-014-001` | **Rejected** | Per-version identity and the newly added aggregate fields are preserved and revalidated. However, `verify_matrix()` only checks that aggregate `command` is a list. Replacing the matrix command with `[]` still lets preflight exit `0` and create `preflight.json`, although runbook §4 requires the matrix index to record exact command argv. The requested regression table also omits this aggregate invalid-value case. |
| `CR-M4-014-002` | **Pass** | Pytest starts first; the active producer emits suite-start and READY with the runner nonce/PID, and observation is accepted only after that barrier. Prefilled, stale, wrong-nonce and missing observations remain fail-closed. |
| `CR-M4-014-004` | **Pass** | Debug now rejects the former path-shaped four-field fabrication and validates the attempt, failed result, raw logs, preflight checksum and frozen chain before executing a bounded node. A runner-generated formal FAIL supports the positive diagnostic path. |
| `CR-M4-014-007` | **Pass** | Observation content now carries candidate SHA and acceptance mode. Expected post-reservation failures retain repository identity, attempt, frozen/preflight chain, available producer/manual checksums, timestamps, exit and raw-log locators in `results/result.json`. |

### Remaining correction and minimum acceptance

For `CR-M4-014-001`, require aggregate matrix `command` to be a non-empty list of non-empty string
argv elements, consistent with the per-version validation. Add a preflight regression for an empty
or otherwise invalid aggregate argv; it must exit non-zero, retain the machine-readable FAIL
bundle, and not create `preflight.json`. This is a focused correction only; the three findings that
passed above must not be reopened unless that change directly regresses them.

### Second re-review verification

```text
PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py
39 passed in 44.96s

python3 -m py_compile scripts/candidate_gate.py tests/test_candidate_gate.py
exit 0

git diff --check
no output

Aggregate identity reproduction:
matrix-index.json command replaced with []
preflight exit                         0
preflight.json created                True
```

Developer should revise only this aggregate argv validation and its direct regression, reply below
this section, and change YAML status to `Revised`. Do not commit before the next Designer review
and USER approval of the complete proposed commit message and file list.

## Designer final re-review — 2026-08-18

**Disposition: PASS — `CR-M4-014-001` is resolved; all seven review findings are closed.**

The aggregate matrix command is now required to be a non-empty argv list whose elements are
non-empty strings. The reported `command=[]` reproduction is covered by the aggregate identity
regression and now fails before preflight PASS evidence can be created. The focused change does not
regress the three findings cleared in the preceding review.

### Final verification

```text
PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py \
  -k 'preflight_rejects_incomplete_matrix_aggregate_identity'
7 passed, 33 deselected in 3.86s

PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py
40 passed in 57.33s

python3 -m py_compile scripts/candidate_gate.py tests/test_candidate_gate.py
exit 0

git diff --check
no output
```

This closes the Designer implementation review only. Before committing, Developer must provide the
complete milestone commit title, 60–100 word English bullet-list body and exact file list for USER
approval under `docs/roles/workflow.md`.
