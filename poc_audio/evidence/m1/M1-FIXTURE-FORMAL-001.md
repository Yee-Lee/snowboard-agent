# M1-FIXTURE-FORMAL-001 — Formal Fixture Acquisition

Status: `PASS`

## Delivery contribution

This evidence closes the controlled native-capture acquisition portion of the
M1 fixture gate. Raw WAV files, their local manifest and the detailed summary
remain in the Git-ignored controlled fixture revision; this tracked record
contains only sanitized counts and hashes.

## Baseline and reviewed result

- Pi recording source SHA: `9055ac4c7dd13c9fdd9599e2eefb765b4d634dc8`
- Native capture: 48 kHz, stereo, S32_LE via direct `hw:` access
- Complete local manifest: 100 / 100 valid files, SHA-256 present for every
  record; manifest SHA-256 `0072a95613d90664d09aa9e11274e3589d9dbcbb786047b060b420cebcddfabf`
- Local verification summary SHA-256:
  `c5d8c87d2507124af14a9ddccce36bf74a30e7fe11ffb0bf7a28188206679c8c`

| Check | Result |
| --- | --- |
| Clear speech | `PASS`, 25 clips |
| Natural pause | `PASS`, 25 clips |
| Silence | `PASS`, 25 clips |
| Ambient noise | `PASS`, 25 clips |
| ASR references | `PASS`, all 50 planned reference IDs recorded |
| Non-speech observation | `PASS`, 600 seconds |
| Native metadata/checksums | `PASS`, every record is 48 kHz / 2 channels / 4-byte samples with a checksum |
| Cleanup | `PASS`, no partial files and no ALSA device owner |

Follow-up technical and human sample review:
[M1 Fixture Formal Sampling](M1-FIXTURE-FORMAL-SAMPLING-001.md) — `PASS WITH
OBSERVATION`; the exact Formal 60-item complement, fixed 14-item technical
sample, and User/Designer 10 / 10 speech listening review are recorded.

## Boundary and remaining review

The completed revision is retained under the controlled local relative fixture
path `poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1/` and is not
committed to Git. This is not yet fixture-set `FROZEN`: delivered-format
conversion/checksums, catalog and label review, and Designer/Tester metrics
freeze remain required before M1 exit or M2 entry.
