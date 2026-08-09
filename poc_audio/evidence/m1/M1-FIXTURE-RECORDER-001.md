# M1-FIXTURE-RECORDER-001 — Controlled Recorder Dry Run

Status: `PASS`

## Delivery contribution

This evidence advances the final delivery checklist's controlled-fixture,
reproducible-program, and data-safety requirements. It verifies the recorder's
non-recording safety controls on the target Pi; it is not VAD/ASR quality or
fixture-audio evidence.

## Baseline and method

- Source SHA: `6cb18975ec6f528670754a8f31e81bfa71776f68`
- Tester runtime: Raspberry Pi 5 Model B Rev 1.1, aarch64, Debian 13,
  Python 3.13.5.
- The environment pre-test passed with clean workstation and Pi worktrees at
  the same SHA, visible capture/playback devices, and no audio device owner.
- Tested commands:
  - `PYTHONPATH=poc_audio/src python3 -m unittest discover -s poc_audio/tests -v`
  - `bash poc_audio/tools/m1_fixture_record.sh --list`
  - `bash poc_audio/tools/m1_fixture_record.sh --record asr-clear-001`

## Reviewed result

| Check | Result |
| --- | --- |
| Recorder and fixture-plan unit tests | `PASS`, 9/9 |
| Planned capture set | `PASS`, exactly 100 fixture IDs |
| Explicit authorization guard | `PASS`, recording command exited before invoking capture without `--confirm-authorization` |
| Raw WAV creation during dry run | `PASS`, none created |
| Pi worktree after dry run | `PASS`, clean |

No recording command was authorized. No raw PCM, WAV, transcript, endpoint,
account, credential, absolute operator path, or device identifier was added to
tracked evidence.

## Gate decision

The controlled recorder is reproducible on the target Pi and protects the
pre-authorization boundary. It remains `PENDING USER AUTHORIZATION AND
RECORDING`; the fixture catalog is not frozen and real candidate testing is not
permitted.
