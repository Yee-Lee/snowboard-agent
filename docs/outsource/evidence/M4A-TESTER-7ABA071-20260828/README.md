# M4A Tester portable sign-off — candidate 7aba071

## Identity and disposition

| Field | Value |
| :--- | :--- |
| Candidate SHA | `7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d` |
| Tester run ID | `m4a-7aba071-20260828-p01` |
| Portable matrix | **Pass** |
| Target status | Pending Designer candidate freeze |

Raw logs and machine-readable results remain Git-external under
`<tester-run-root>/m4a-tester-evidence-7aba071-20260828-p01/`. The candidate was
checked out detached and every protected path remained clean.

## Anti-flake re-verification

Before the matrix, Tester executed
`test_m4a_ipc_001_actual_asr_process_handles_coalesced_and_fragmented_input[False]`
in 20 independent CPython 3.11 pytest processes. All 20 passed. This directly
re-verifies the exit-oracle correction that rejected candidate `ed1b2cf`.

## Formal portable matrix

| Python | Result | Counts |
| :--- | :--- | :--- |
| CPython 3.11.16 | Pass | 167 passed; 0 failed/skipped/xfailed |
| CPython 3.12.3 | Pass | 167 passed; 0 failed/skipped/xfailed |
| CPython 3.13.15 | Pass | 167 passed; 0 failed/skipped/xfailed |

`matrix-index.json` has status `Pass`; all three result files bind candidate
`7aba0719e9f7858a68b44f28d2d99e3d3d2ef25d` and run
`m4a-7aba071-20260828-p01`. Each runner used a 120-second hard suite timeout,
the tracked 13-module M4A manifest, marker `not rpi`, an empty inherited
`PYTHONPATH`, and disabled third-party pytest entry-point autoload.

## Gate transition

This evidence is Tester portable sign-off only. It does not reuse Developer
results, freeze the candidate, or claim Pi acceptance. Designer must next review
and freeze this same protected SHA. After freeze, Tester will use a new target
run ID, reboot the Pi, verify a clean baseline, and run fresh product,
preflight, complete offline acceptance, inheritance and final reconciliation.
