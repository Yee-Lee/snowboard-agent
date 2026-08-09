# M1-FIXTURE-STAGE-001 — Two-Stage Selection

Status: `PASS`

## Delivery contribution

This evidence advances the controlled-fixture and reproducible-program portions
of the final delivery checklist. It confirms that the collection tooling can
separate the operational Pilot from Formal completion without changing the
approved 100-item formal gate.

## Baseline and method

- Source SHA: `0846a904f1a642d59a4619dd4881ce713ac4b586`
- Tester runtime: Raspberry Pi 5 Model B Rev 1.1, aarch64, Debian 13.
- Pi worktree was clean before and after the dry run.
- Tested commands:
  - `bash poc_audio/tools/m1_fixture_record.sh --list --stage pilot`
  - `bash poc_audio/tools/m1_fixture_record.sh --list --stage formal`

## Reviewed result

| Check | Result |
| --- | --- |
| Pilot selection | `PASS`, exactly 40 fixture IDs |
| Formal selection | `PASS`, exactly 60 remaining fixture IDs |
| Stage overlap / bypass | `PASS`, Formal validation still requires the complete 100-item set |
| Audio capture or WAV creation | `NOT RUN`, no authorization flag was supplied |
| Pi worktree after test | `PASS`, clean |

## Gate decision

The two-stage collection workflow is reproducible on the target Pi. Stage A is
an operational Pilot only; it does not alter the 100-item/50-utterance formal
gate and cannot advance or reject VAD/ASR candidates. Fixture authorization,
recording, complete formal review, and the Core AudioInput decision remain
open M1 conditions.
