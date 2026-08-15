# DELIVERY-M1-FIXTURE-METRICS-FREEZE-001 — Fixture and Metric Freeze Packet

Status: `ACCEPTED / FROZEN`
Decision Date: 2026-08-15
Decision Approver (Designer): User
Verification (Tester): Test Controller

## Purpose

This packet records the formal freeze of the M1 fixture set, catalog metadata,
and evaluation metric rules. Real candidate evaluation may proceed under these
frozen rules.

## Fixed inputs accepted for freeze

| Item | Frozen value | Evidence |
| --- | --- | --- |
| Native fixture revision | `m1-authorized-zh-tw-v1-pilot-r1`, 100 files | `fixture_manifest.json` SHA `0072a95613d90664d09aa9e11274e3589d9dbcbb786047b060b420cebcddfabf` |
| Native capture | 48 kHz / stereo / `S32_LE` via direct `hw:` | [Formal acquisition](../evidence/m1/M1-FIXTURE-FORMAL-001.md) |
| Completeness and integrity | 25 clips per VAD class, 50 ASR references, 600 seconds non-speech | Formal verify `PASS` |
| Technical/listening review | Formal 60-item complement; fixed 14-item technical sample and 10/10 speech listening review | [Formal sampling](../evidence/m1/M1-FIXTURE-FORMAL-SAMPLING-001.md) |
| Catalog boundary | [fixture_catalog_v1.json](../fixtures/authorized/fixture_catalog_v1.json) SHA `7d89fe13e53d1fbd4a3f4d1ace81bd6291c236008218be93f4fe87cf6388b677` | plan and local-manifest hashes; raw audio stays outside Git |
| Delivered fixture revision | `delivered_fixture_manifest.json` SHA `1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2`, 100 files | [Delivered revision evidence](../evidence/m1/M1-FIXTURE-DELIVERY-001.md) |
| ASR normalization/scoring | `metrics_v1.md` ASR section | NFKC, lowercase Latin, remove punctuation/whitespace; preserve Han/Latin/digits |
| VAD/ASR/TTS metric rules | [metrics_v1.md](../fixtures/metrics_v1.md) SHA `6372fd60c5f4d30cdba8baa8ca9300737e62dbba28795d643d99e7bbbf8f0d72` | frozen numeric gates approved 2026-08-15 |

## Approval record

| Decision | Approver | Status | Evidence |
| --- | --- | --- | --- |
| Native acquisition and sampled listening | User / Designer | `PASS` | `M1-FIXTURE-FORMAL-001`, `M1-FIXTURE-FORMAL-SAMPLING-001` |
| ASR reference categories and normalization v1 | User / Designer | `PASS` | This packet, `metrics_v1.md` |
| VAD timing labels | User / Designer + Tester | `PASS` | [M1-FIXTURE-VAD-LABELS-001](../evidence/m1/M1-FIXTURE-VAD-LABELS-001.md) |
| Delivered-format fixture revision | User / Designer + Tester | `PASS` | [M1-FIXTURE-DELIVERY-001](../evidence/m1/M1-FIXTURE-DELIVERY-001.md) |
| Fixture/metric set frozen | User / Designer + Tester | `PASS / FROZEN` | All rows above plus clean-SHA reproduction |
