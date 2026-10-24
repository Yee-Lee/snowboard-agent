# M4A Tester evidence summary — 2026-08-28

## Identity and verdict

| Field | Value |
| :--- | :--- |
| Candidate SHA | `306dbc96585d1eef55ba0c6380e2eeceaa2057fc` |
| Accepted Audio SHA | `5694ead4ba6be928fdb4dbdf6da7155b214d72bd` |
| Portable run ID | `m4a-306dbc9-20260828-p01` |
| Pi acceptance run ID | `m4a-306dbc9-20260828-pi01` |
| Platform | Raspberry Pi 5, aarch64, 4 GB, CPython 3.13.5 |
| Verdict | **Fail** |

Raw Pi evidence remains Git-external under the immutable run alias
`<pi-run-root>/306dbc9-20260828-a01/`. Raw logs are not copied into Git because
the network trace contains absolute work paths and process arguments. This file
records only sanitized results and locators.

## Portable matrix

| Python | Result | Counts |
| :--- | :--- | :--- |
| CPython 3.11.16 | Pass | 160 passed; 0 failed/skipped/xfailed |
| CPython 3.12.3 | Pass | 160 passed; 0 failed/skipped/xfailed |
| CPython 3.13.15 | Pass | 160 passed; 0 failed/skipped/xfailed |

Matrix status was `Pass`; all three results used the same candidate SHA and run
ID. JUnit covered all 13 M4A portable modules. Candidate-runner regression was
`14 passed`; adjacent repository regression was `444 passed, 28 deselected`.

## Product and target preparation

- Locked input artifacts: all tracked SHA-256 values matched.
- Fresh offline whisper build: Pass; aarch64 worker SHA-256 begins `72f590be`.
- Fresh offline product install: Pass; 8 wheels; install schema v4.
- Matcha closure: 362 files; tree SHA-256 begins `5e4f8625`.
- Product preflight: Pass; network attempt count 0 during preparation.
- Candidate preflight: Pass; portable, config, hardware and product identity all
  bind the same candidate SHA.

## Formal Pi acceptance

Canonical sanitized command:

```text
<python-3.13> scripts/candidate_gate.py --repo <clean-candidate> accept \
  --candidate-sha 306dbc96585d1eef55ba0c6380e2eeceaa2057fc \
  --run-id m4a-306dbc9-20260828-pi01 \
  --preflight <acceptance-root>/preflight.json \
  --suite tests/milestones/test_m4_local_voice.py \
  --timeout-seconds 600 --output <acceptance-root>
```

The suite collected seven tests, entered
`test_m4a_asr_001_and_002_real_persistent_two_turns`, and timed out after 600
seconds. The runner wrote `accept-failure.json`, stdout/stderr and network trace;
it correctly did not create a PASS `result.json`, JUnit or finalized cards.
Candidate-specific descendants were terminated. One per-process ASR temp
directory remained after the forced timeout.

## Test ID disposition

| Test ID | Portable | Pi / formal disposition |
| :--- | :--- | :--- |
| `M4A-CFG-001` | Pass | Portable scope complete |
| `M4A-LOCK-001` | Pass | Preflight Pass; formal reconciliation blocked |
| `M4A-IPC-001` | Pass | **Fail** — real coalesced BEGIN/FRAME deadlock |
| `M4A-ASR-001` | Pass | **Fail** — real IPC/finite-input timeout |
| `M4A-ASR-002` | Pass | Blocked by the same ASR terminal wait |
| `M4A-ASR-003` | Pass | Blocked before real recovery node |
| `M4A-TTS-001` | Pass | **Fail (diagnostic, default environment)** — three native thread leaks; unchanged node passes in 5.43 s with pre-start `OPENBLAS_NUM_THREADS=1` |
| `M4A-TTS-002` | Pass | **Fail (target test)** — formal node omits deferred→Level 2; external contract-aligned recovery diagnostic passes in 6.11 s with zero cleanup deltas |
| `M4A-PRIV-001` | Pass | Blocked before formal Pi node |
| `M4A-OFF-001` | Collector Pass | **Fail** — stalled formal ASR produced 72 IPv4/IPv6 trace lines; direct whisper and completed delayed-adapter controls produced zero, so the syscall-only trace does not yet identify the userspace caller |
| `M4A-RES-001` | Collector Pass | Blocked by ASR; combined row remains Pending |
| `M4A-PKG-001` | Pass | Product install/preflight Pass; Pi node diagnostic Pass only |
| `M4A-INH-001` | Generator Pass | Formal inheritance blocked; no file generated |

Diagnostic results are included only to make the first rejection complete. The
successful TTS rerun proves the minimal thread-policy correction but is not a
production-launch fix. The successful Level-2 recovery diagnostic isolates a
target-test contract mismatch. Neither result is promoted to a formal PASS card
or can be combined with a later run.

## Blocking handoff

See `docs/reviews/TR_dev_M4_I.md` for four Blocking findings, reproduction,
root cause, expected/actual behavior, preferred correction and minimum
re-verification commands.
