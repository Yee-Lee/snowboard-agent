# Developer Progress — M4

## Candidate gate reform (WP-PROC-01 to WP-PROC-03)

| Work package | Estimate | Plan | Status |
| :--- | :--- | :--- | :--- |
| WP-PROC-01 | 0.75 day | Keep a minimal candidate-gate CLI for portable, matrix, preflight, acceptance, and unrestricted diagnostic runs. | Complete |
| WP-PROC-02 | 0.5 day | Keep focused regressions for exact SHA, protected paths, scope split, matrix completeness, timeout, checksum recording, and run-output reuse. | Complete |
| WP-PROC-03 | 0.25 day | Run the CPython 3.11/3.12/3.13 matrix only for candidate branches or manual dispatch. | Complete |
| Developer verification | 0.5 day | Run the focused gate suite on the designated local Python minor and report the handoff commands. | Complete with environment note |

## Scope and constraints

- Authority: `PM-OUT-260818-018-m4-portable-gate-cost-correction` and `docs/runbooks/candidate_hardware_gate.md`.
- This delivery changes only development/acceptance tooling, tests, metadata, and CI; it does not alter production M3 behavior or claim a frozen candidate, Pi PASS, or Tester sign-off.
- Candidate identity is always caller-supplied. The runner fails before a suite or hardware operation when SHA, protected paths, matrix, runtime/checksum input, or run isolation is invalid; manual evidence remains in the milestone report/card rather than this runner.
- WP-PROC-04 remains owned by Tester and is not performed by this Developer fast loop.

## Developer verification

- `tests/test_candidate_gate.py` covers only the retained checks; manual handshake, debug FAIL-bundle authorization, multi-layer checksum-chain and six command-level dry-run cases were removed.
- `PYTHONPATH=src python3 -m pytest -q tests/test_candidate_gate.py` → `10 passed` on the designated local Python minor.
- `python3 -m py_compile scripts/candidate_gate.py` → passed.
- Available non-RPi regression was split to stay within the local command bound: core/M1 groups `166 passed`; M2 groups `36 passed`; M3 group `34 passed, 20 deselected` with one environment-only failure in `test_m3_aud_001` because `samplerate==0.2.4` is absent. The current local Python has no `pip` module, so that declared dev dependency cannot be installed here. CI installs `.[dev]` before executing the 3.11/3.12/3.13 matrix.
