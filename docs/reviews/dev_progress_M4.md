# Developer Progress — M4

## Candidate gate reform (WP-PROC-01 to WP-PROC-03)

| Work package | Estimate | Plan | Status |
| :--- | :--- | :--- | :--- |
| WP-PROC-01 | 1.5 days | Implement a fail-closed candidate-gate CLI for portable, preflight, acceptance, debug, and PASS-only matrix evidence flows. | Complete |
| WP-PROC-02 | 1 day | Add fixture-backed regressions for DRY-SHA, DRY-DIRTY, DRY-MATRIX, DRY-TIMEOUT, DRY-MANUAL, and DRY-RUN-ID. | Complete |
| WP-PROC-03 | 0.5 day | Add a CPython 3.11/3.12/3.13 portable workflow and bounded aggregation step. | Complete |
| Developer verification | 0.5 day | Run the focused gate suite on the designated local Python minor and report the handoff commands. | Complete with environment note |

## Scope and constraints

- Authority: `docs/runbooks/candidate_hardware_gate.md` and `OUT-PROCESS-2026-001`.
- This delivery changes only development/acceptance tooling, tests, metadata, and CI; it does not alter production M3 behavior or claim a frozen candidate, Pi PASS, or Tester sign-off.
- Candidate identity is always caller-supplied. The runner must fail before a suite or hardware operation when identity, protected paths, matrix, readiness/manual evidence, timeout, or run isolation is invalid.
- WP-PROC-04 remains owned by Tester and is not performed by this Developer fast loop.

## Developer verification

- `tests/test_candidate_gate.py` was rerun in bounded groups → all `40` cases passed on CPython 3.12, including the `command=[]` matrix aggregate false-green regression and the second `CR-M4-014` revision set.
- `python3 -m py_compile scripts/candidate_gate.py` → passed.
- Available non-RPi regression was split to stay within the local command bound: core/M1 groups `166 passed`; M2 groups `36 passed`; M3 group `34 passed, 20 deselected` with one environment-only failure in `test_m3_aud_001` because `samplerate==0.2.4` is absent. The current local Python has no `pip` module, so that declared dev dependency cannot be installed here. CI installs `.[dev]` before executing the 3.11/3.12/3.13 matrix.
