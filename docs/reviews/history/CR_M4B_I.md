---
requestor: "Designer"
owner: "Developer"
status: "Resolved"
---

# CR_M4B_I — M4B foundation candidate final alignment

## Review disposition

**RESOLVED — both Blocking findings are closed and the foundation candidate is ready for a
commit proposal.**

Tester reported PASS, but Designer final alignment found two blocking roots: lifecycle E1 cannot
reliably finish or enter recovery, and the focused suite does not implement the approved coverage
matrix. The reviewed candidate is the unstaged worktree delta based on
`8d8f7aa166911d65c23b67b6dad4ef514bed3240`, including the 30 modified files reported by
`git diff --name-only` plus untracked `tests/test_m4b_foundation.py`.

Authoritative basis:

- `docs/implement/m4b_foundation_revision.md` §§3.2–3.3, 5.3, 6–8 and 10.
- `docs/test_spec/test_spec_M4B_foundation.md`, especially FND-WAKE-002, FND-ACT-001–003,
  FND-REP-001, FND-LIFE-001–003, FND-R1-001, FND-CONV-001–002, FND-SM-001, FND-RM-001 and
  FND-REG-001.

## Blocking findings

### CR-M4B-001 — Invalid lifecycle proof loses recovery state or deadlocks convergence

- **Contract basis**: Foundation §§3.2–3.3 and 7 require a missing lifecycle proof or unusable
  Engine to enter E1, retain the lifecycle target through Level 1/2/3, wait for any required RM
  recovery, and clear the Product Session only after all proof barriers. Section 7 fixes the phase
  order as `workers → conversation_close → recovery → complete`.
- **Location**: `src/sbd/core/state_manager/manager.py:407-470` and `:873-886`, with the related
  target selection in `src/sbd/core/state_manager/convergence.py:158-187`.
- **Reproducible evidence**: an event-driven pytest reproduction used the existing `make_sm()`,
  `_WakeAckElapsed`, `RecoveryPort` and lifecycle fakes, then ran
  `PYTHONPATH=src:. pytest -q /tmp/test_m4b_close_repro.py -s`. Both required assertions failed:

  ```text
  session-end ConversationCloseProof(False, False, True)
    observed: ('ERROR', 'conversation_close', 0)

  ConversationOpenRejected(cleanup_proven=True, engine_usable=False)
    observed: ('IDLE', [], None)  # state, recovery.begun, pending

  2 failed
  ```

- **Expected / actual**: successful Level 1 cleanup of an invalid session-end close should advance
  the error convergence past `conversation_close`; it currently removes the record but leaves that
  phase forever. A known-unusable Engine must remain behind the RM recovery boundary; the current
  code folds `engine_usable` into `cleanup_proven`, lets Level 1 overwrite the distinction, reports
  no destroyed backend, and can return directly to IDLE.
- **Impact**: one path permanently blocks new sessions; the other accepts a new session on a backend
  explicitly reported unusable. Replacement close has the same unsafe root and can either stall or
  lose the recovery requirement. A green happy-path suite cannot release this candidate.
- **Preferred fix**:
  1. Preserve cleanup proof and Engine usability as distinct lifecycle state; do not assign their
     conjunction to `record.cleanup_proven`.
  2. On lifecycle E1, converge the target, remove it only after cleanup proof, and always move an
     existing pending phase out of `conversation_close` once the target is proven.
  3. Treat `engine_usable=False` as recovery-required. After Level 1 cleanup, route through the
     lifecycle control's Level 2 `force_abort()` report so the stable destroyed backend key reaches
     `RecoveryControl.begin_recovery()`. A known-unusable Engine with no usable backend identity must
     fail closed, not return IDLE. Shutdown keeps the existing no-rebuild rule.
  4. Do not increment generation or start a replacement open on any invalid close result.
- **Minimum acceptance**: add deterministic tests for incomplete session-end close with Level 1
  success, incomplete replacement close, unusable open, unusable replacement close and unusable
  session-end close. Assert phase progression, no new open before proof, the exact RM recovery key,
  no IDLE before `_RecoveryCompleted`, and successful completion after recovery. Retain Level 2
  timeout/exception → Level 3 coverage.

**Developer response:** Corrected. `InFlightRecord` now preserves `request_terminal_proven`,
`cleanup_proven`, `engine_usable` and `force_abort_proven` independently. `DefaultSessionConverger`
retains done-but-unproven/private unusable targets, forces unusable Engines through Level 2, and
fails closed as `unusable_backend_unidentified` when no stable backend key is returned.
`StateManager._lifecycle_e1()` advances an existing pending close to recovery, preserves shutdown
precedence, starts RM recovery from the exact Level 2 report, and never opens a replacement after
invalid proof. Covered by
`test_m4b_foundation_cr_m4b_001_incomplete_session_close_advances`,
`...incomplete_replacement_never_opens_new_generation`,
`...unusable_close_waits_for_recovery`, `...level1_escalates_to_level2`,
`...level2_failure_is_level3_fatal`, and `...unusable_engine_requires_backend_identity`, plus the
unusable-open WAKE case. Focused result: **68 passed**.

### CR-M4B-002 — The focused suite is a false-green subset of the approved test specification

- **Contract basis**: Foundation §10 requires all nine coverage groups. The approved test spec
  supplies observable cases for every named Test ID; its FND-REG-001 guard is specifically intended
  to prevent a schema migration from passing through aliases or positional construction.
- **Location**: `tests/test_m4b_foundation.py:103-468` and the unsupported completeness claim in
  `docs/status/development.md` under “Test IDs” and “Verification evidence”.
- **Reproducible evidence**: `rg -n '^def test_m4b_foundation' tests/test_m4b_foundation.py` finds
  only 15 test functions (17 collected cases). Direct inspection shows that the suite has no
  executable FND-R1 case and omits, among others: open exception/wrong-type/unusable-Engine and
  WAKE interrupt/error/shutdown; tool and action-error/default routes; empty end; incomplete close
  proofs; stale session/correlation/task identities; Level 2/3 and RM recovery barriers; and most
  SessionContext transition assertions. The two failures in CR-M4B-001 are mandatory cases that the
  claimed 17-pass suite never exercises.
- **Expected / actual**: the focused suite must prove the approved rows, not merely mention all 19
  Test IDs in development status or combine IDs in test names. Current PASS count proves only a
  small happy-path subset and allowed two contract failures through.
- **Impact**: Tester and Designer receive a false release signal; regressions in cleanup, recovery,
  action routing and stale identity remain invisible.
- **Preferred fix**:
  1. Implement every observable row in FND-WAKE-002, FND-ACT-001–003, FND-REP-001,
     FND-LIFE-001–003, FND-R1-001, FND-CONV-001–002, FND-SM-001 and FND-RM-001. Parameterization is
     welcome, but each row must have a deterministic assertion and no wall-clock race.
  2. Replace the positional-constructor alias evasion at `tests/test_m4b_foundation.py:108-110`
     with `inspect.signature(LLMResponse).bind(...)` (or an equivalent non-construction signature
     assertion), so the structural guard can enforce all real constructor calls without an
     exception.
  3. Expand the AST guard to resolve direct imports, import aliases, qualified module attributes and
     simple assignment aliases. Continue rejecting positional args, `**kwargs`, and missing required
     keywords, and report every violation as `path:line`.
  4. Update `docs/status/development.md` only after the implementation and evidence are true; list
     actual covered cases and commands rather than treating Test-ID labels as coverage.
- **Minimum acceptance**: the corrected focused suite must fail against the current two
  reproductions, pass after CR-M4B-001 is fixed, and demonstrate all required route/proof/recovery/
  stale-identity branches. Then rerun the immutable 99-node anti-deletion check, zero-skip baseline
  regression and full repository suite. Tester must independently verify the revised candidate
  before Designer re-review.

**Developer response:** Corrected. The focused suite now exercises the speak/tool × ok/error ×
KEEP/REPLACE matrix, speak/tool/rest END_SESSION matrix, invalid THINK routes, payload identity,
WAKE failures and interruption, all four stale identity dimensions, premature lifecycle notice,
missing/invalid/double/late wiring, lifecycle concurrency, Reasoner generation/admission, R1
canonical/noncanonical boundaries, Level 1/2/3, RM recovery and SessionContext proof fields. The
schema check uses `inspect.signature(...).bind`; `_invalid_llm_response_constructor_lines()` resolves
direct imports, import aliases, qualified module attributes and transitive simple assignments, with
an executable alias-form regression. Evidence: focused **68 passed**; immutable nodes **99 retained,
0 missing**; strict baseline/JUnit **99 passed, failures=0, errors=0, skipped=0**; full suite exit 0
with **770 passed and 2 pre-existing optional-samplerate skips**; compileall and diff check pass.

## Advisory

- The changes to `src/sbd/cognition/reasoner.py` remain compile migration only. Its existing product
  fallback policy is not accepted as implementation of the new R1/R2/E1 contract; do not claim a
  cognition/product PASS until that separately gated rewrite opens.

## Developer response and resubmission

Respond below each finding with the changed symbols, test node IDs and exact verification output.
Do not create a commit while this review is Open. After Developer revision, route the candidate to
Tester; Designer will only re-check these findings, their direct impact and new regressions.

## Tester independent verification

- **Verification date**: 2026-09-11
- **Verifier**: Tester
- **Target**: Revised foundation candidate worktree delta (`8d8f7aa166911d65c23b67b6dad4ef514bed3240` + unstaged/untracked changes)
- **Commands and results**:
  - `timeout 60s env PYTHONPATH=src pytest -o addopts='' -v tests/test_m4b_foundation.py`: **68 passed in 4.85 s** (0 fail, 0 error).
  - Anti-deletion check vs `docs/test_spec/baselines/m4b_foundation_node_ids.txt`: baseline 99, post 99, missing **0**.
  - Strict baseline JUnit XML (`tests/milestones/test_m1_foundation.py` ... 7 files): **99 passed in 16.19 s**, `failures=0`, `errors=0`, `skipped=0`.
  - Full test suite: **770 passed, 2 skipped, 29 deselected in 62.78 s** (both skips are pre-existing M3 audio tests lacking optional `samplerate`).
  - `python3 -m compileall -q src tests` and `git diff --check`: **PASS** (exit code 0).
- **Finding verification**:
  - **CR-M4B-001 verified**: Incomplete session-end close advances past `conversation_close`; incomplete replacement close never increments generation or launches new open; unusable close/open triggers Level 2 recovery with exact destroyed backend key `backend.cognition.reasoner.llm` and holds session until recovery releases; unusable Engine without backend identity fails closed (`unusable_backend_unidentified`); Level 2 timeout/exception escalates to Level 3 fatal (`ConvergenceFatalError`).
  - **CR-M4B-002 verified**: Focused suite implements the full 68-test matrix covering all approved branches; `inspect.signature(LLMResponse).bind` verifies schema without invalid positional runtime calls; AST structural guard checks direct imports, import aliases, qualified attribute paths, and assignment aliases, with regression tests confirming correct rejection.
- **Disposition**: **PASS** on candidate correction.
- **Next owner**: **Designer** for final alignment, review closure (`Resolved`), and candidate commit proposal.

## Designer final re-review

- **Review date**: 2026-09-11
- **CR-M4B-001**: **Resolved**. Independent inspection confirms that lifecycle request-terminal,
  cleanup, Engine usability and force-abort proofs remain distinct; incomplete close advances out
  of `conversation_close`; known-unusable Engines require a stable destroyed-backend identity and
  wait behind RM recovery; invalid replacement proof cannot open a new generation.
- **CR-M4B-002**: **Resolved**. The focused suite now collects and passes 68 deterministic cases,
  including the required action, WAKE failure, lifecycle identity, R1, Level 1/2/3 and recovery
  branches. The AST guard covers direct, aliased, qualified and assignment-based constructor names,
  while the positional schema check uses `inspect.signature(...).bind`.
- **Designer verification**:
  - Focused foundation: **68 passed in 5.37 s**.
  - Immutable baseline: **99 retained, 0 missing**; strict JUnit: **99 passed, 0 failures, 0 errors,
    0 skipped**.
  - Full repository: **770 passed, 2 pre-existing optional-samplerate skips, 29 deselected** in
    85.21 s.
  - `python3 -m compileall -q src tests` and `git diff --check`: **PASS**.
- **Disposition**: no Blocking or Advisory item remains open. This resolution permits a commit
  proposal but does not authorize commit or push without explicit USER approval.
