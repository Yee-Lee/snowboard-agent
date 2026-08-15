# DELIVERY-M1-FIXTURE-METRICS-FREEZE-001 — Fixture and Metric Freeze Packet

Status: `REVIEW_READY / NOT_FROZEN`

## Purpose

This packet advances M1's frozen-fixture and frozen-metric exit condition. It
does not authorize a real candidate run. Its purpose is to let the Designer
accept or reject a fully stated fixture boundary before any candidate result is
observed.

## Fixed inputs proposed for acceptance

| Item | Proposed frozen value | Evidence |
| --- | --- | --- |
| Native fixture revision | `m1-authorized-zh-tw-v1-pilot-r1`, 100 files | `fixture_manifest.json` SHA `0072a95613d90664d09aa9e11274e3589d9dbcbb786047b060b420cebcddfabf` |
| Native capture | 48 kHz / stereo / `S32_LE` via direct `hw:` | [Formal acquisition](../evidence/m1/M1-FIXTURE-FORMAL-001.md) |
| Completeness and integrity | 25 clips per VAD class, 50 ASR references, 600 seconds non-speech | Formal verify `PASS` |
| Technical/listening review | Formal 60-item complement; fixed 14-item technical sample and 10/10 speech listening review | [Formal sampling](../evidence/m1/M1-FIXTURE-FORMAL-SAMPLING-001.md) |
| Catalog boundary | [fixture_catalog_v1.json](../fixtures/authorized/fixture_catalog_v1.json) SHA `7334ab64b096a304f6387a618f1d1f8c7131fa98ec9b33efa1edd3a19003af11` | plan and local-manifest hashes; raw audio stays outside Git |
| Delivered fixture revision | `delivered_fixture_manifest.json` SHA `1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2`, 100 files | [Delivered revision evidence](../evidence/m1/M1-FIXTURE-DELIVERY-001.md) |
| ASR normalization/scoring | `metrics_v1.md` ASR section | NFKC, lowercase Latin, remove punctuation/whitespace; preserve Han/Latin/digits |
| VAD/ASR/TTS metric rules | [metrics_v1.md](../fixtures/metrics_v1.md) SHA `2c575431d7be1d47ed1b1bba2df8dfde8b246bbe562d6d13ced7c09b9f7a7bcc` | proposed numeric gates approved 2026-08-08; full fixture acceptance pending |

## Blocking work before freeze

1. Complete User / Designer confirmation on ASR reference categories and normalization v1.
2. Run the Tester reproduction packet at the final clean SHA, then record the
   Designer acceptance in `m1_frozen_gates_draft.md`.

## Approval record

| Decision | Approver | Status | Evidence |
| --- | --- | --- | --- |
| Native acquisition and sampled listening | User / Designer | `PASS` | `M1-FIXTURE-FORMAL-001`, `M1-FIXTURE-FORMAL-SAMPLING-001` |
| ASR reference categories and normalization v1 | User / Designer | `PENDING` | This packet, `metrics_v1.md` |
| VAD timing labels | User / Designer + Tester | `PASS` | [M1-FIXTURE-VAD-LABELS-001](../evidence/m1/M1-FIXTURE-VAD-LABELS-001.md) |
| Delivered-format fixture revision | User / Designer + Tester | `PASS` | [M1-FIXTURE-DELIVERY-001](../evidence/m1/M1-FIXTURE-DELIVERY-001.md) |
| Fixture/metric set frozen | User / Designer + Tester | `PENDING` | All rows above plus clean-SHA reproduction |
