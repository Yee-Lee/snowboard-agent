# M1-FIXTURE-DELIVERY-001 — Option A Delivered Fixture Revision

Status: `PASS`

The Core-selected Option A delivered fixture revision has been produced from the
immutable native recording at `poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1/`
and verified on Raspberry Pi 5.

## 1. Specification and provenance

| Item | Value |
| --- | --- |
| Preparer ID | `m1-option-a-delivery-v1` |
| Execution environment | Raspberry Pi 5 / aarch64 (isolated runtime: `samplerate 0.2.4`, `numpy 2.4.2`) |
| Source native manifest SHA-256 | `0072a95613d90664d09aa9e11274e3589d9dbcbb786047b060b420cebcddfabf` |
| Delivered manifest path | `poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1/delivered-option-a-v1/delivered_fixture_manifest.json` |
| Delivered manifest SHA-256 | `1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2` |
| Delivered PCM format | 16 kHz / mono / `S16_LE` |
| Channel mapping | Channel index 0, 24 valid bits, left-aligned |
| Resampling policy | Stateful `libsamplerate` (`sinc_best`, 1:3 ratio, explicit filter tail drain) |

## 2. Verification and cross-validation

The Test Controller verified all 100 derived WAV files against the plan and catalog rules:

| Check | Result |
| --- | --- |
| Record count | `PASS`, exactly 100 WAV files (25 clear speech, 25 pause, 25 silence, 25 noise) |
| PCM format | `PASS`, 100/100 files are 16,000 Hz, 1 channel, 16-bit signed integer (S16_LE) |
| Frame counts and duration | `PASS`, 96,000 frames (6.0s) for clear, 128,000 frames (8.0s) for pause, 192,000 frames (12.0s) for silence/noise |
| Checksum verification | `PASS`, each derived file SHA-256 recomputed and matched `delivered_fixture_manifest.json` |
| Native binding | `PASS`, every record binds to its verified native SHA-256 from `fixture_manifest.json` |

## 3. Disposition

The delivered fixture revision satisfies all Option A conversion and verification
requirements from Core decision `DELIVERY-AUDIO-POC-M3-P4-ACK-004`. It is accepted as
the derived delivery PCM baseline for candidate evaluation.
