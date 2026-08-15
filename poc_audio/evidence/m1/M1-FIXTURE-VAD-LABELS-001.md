# M1-FIXTURE-VAD-LABELS-001 — VAD Timing Label Review

Status: `PASS`

The externally assisted, human-reviewed VAD label index is retained locally at
`poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1/review/vad-labels-v1.json`.
It remains outside Git. Its SHA-256 is
`85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74`.

At the controlled Pi revision, the Test Controller verified:

| Check | Result |
| --- | --- |
| Records | `PASS`, 50 total: 25 clear speech and 25 pause |
| Clear labels | `PASS`, exactly one in-range speech interval per fixture |
| Pause labels | `PASS`, exactly two in-range speech intervals; the internal-pause interval exactly bridges them |
| Fixture binding | `PASS`, every label's native SHA-256 matches the controlled `fixture_manifest.json` record |
| Coverage | `PASS`, exact IDs `asr-clear-001`–`025` and `asr-pause-026`–`050`; no extra IDs |

The labels were created with an external tool and reviewed by the User/Designer.
They are accepted as the M1 VAD timing ground truth for the immutable native
fixture revision. This does not freeze the fixture set: delivered-format
conversion/checksums and final metric acceptance remain required.
