# M1-FAKE-001 — Deterministic Harness Baseline

狀態：`PASS`

## Delivery contribution

This evidence advances the final delivery checklist's reproducible-program and
lifecycle/cleanup requirements. It validates the common harness before any real
VAD, ASR, or TTS candidate is run; it is not candidate quality evidence.

## Baseline and method

- Source SHA: `334825330d8a5a66bddf1a2c64ae80c737aa552a`
- Workstation runtime: Python 3.14.6.
- Tester runtime: Raspberry Pi 5 Model B Rev 1.1, aarch64, Debian 13,
  Python 3.13.5.
- The environment pre-test passed with clean workstation and Pi worktrees at
  the same source SHA and no audio device owner.
- Commands:
  - `PYTHONPATH=poc_audio/src python3 -m unittest discover -s poc_audio/tests -v`
  - `bash poc_audio/tools/run_m1_fake_baseline.sh`
- Raw JSON results remain in Git-ignored evidence directories on each test
  system. They contain no endpoint, account, credential, private path, audio,
  or transcript.

## Reviewed results

| Check | Workstation | Raspberry Pi 5 |
| --- | --- | --- |
| Unit/schema/catalog tests | `PASS`, 7/7 | `PASS`, 7/7 |
| success | `success` | `success` |
| declared error | `error` | `error` |
| timeout | `timeout` | `timeout` |
| cancel | `cancelled` | `cancelled` |
| forced termination | `force_aborted`, worker exit `-9` | `force_aborted`, worker exit `-9` |
| unexpected failures | none | none |

Every scenario reported zero child processes, threads, iterators, streams, and
device owners after completion. Forced termination was used only in the
stubborn-worker scenario.

## Gate decision

The deterministic fake, result schema, manifest/catalog validation, terminal
status handling, and cleanup proof are reproducible on the target Pi at the
specified SHA. The M1 Tester reproduction item is `PASS`.

The tracked fixtures are deterministic fake data only. Licensed or explicitly
project-authorized VAD/ASR audio, final checksums, labels/references, and scoring
definitions remain required before the frozen gate permits real candidate runs.
