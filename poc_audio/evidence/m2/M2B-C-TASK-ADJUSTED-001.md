# M2B C task-adjusted scoring

Date: 2026-08-22  
Status: `OBSERVATIONS COMPLETE / PENDING COMPARATIVE REVIEW`

This is the immutable pre-erratum scoring record. Current comparative totals
must apply
[`M2B-C-REFERENCE-ERRATUM-001`](M2B-C-REFERENCE-ERRATUM-001.md). The original
Pi result and hashes below are intentionally preserved.

The formal Pi run scored 96 controlled rows at clean source SHA
`7fae7f318e3543ae05a1f7abd1ce2e7ef7a8c6b6`. It performed no inference,
model load, or audio access. The committed result contains metrics and text
hashes only; raw CER remains unchanged and separately reported.

| Candidate/profile | Family | Raw | Task-adjusted | Correct raw → adjusted |
| --- | --- | ---: | ---: | ---: |
| Base baseline | Internal | 44/189, 23.28% | 37/187, 19.79% | 3/16 → 4/16 |
| Base baseline | Common Voice | 20/87, 22.99% | 7/87, 8.05% | 2/8 → 5/8 |
| Base prompt | Internal | 31/189, 16.40% | 24/187, 12.83% | 7/16 → 8/16 |
| Base prompt | Common Voice | 12/87, 13.79% | 8/87, 9.20% | 4/8 → 5/8 |
| Small baseline | Internal | 31/189, 16.40% | 20/187, 10.70% | 5/16 → 7/16 |
| Small baseline | Common Voice | 12/87, 13.79% | 4/87, 4.60% | 3/8 → 5/8 |
| Small prompt | Internal | 25/189, 13.23% | 18/187, 9.63% | 9/16 → 11/16 |
| Small prompt | Common Voice | 10/87, 11.49% | 5/87, 5.75% | 4/8 → 5/8 |

Bounded C-v1 accepts only its frozen Traditional-to-Simplified character map,
Chinese integers 0–9999, and `百分之` equivalence. It does not accept homophones
or domain aliases and is not a general product normalizer. Runtime
post-processing is not proposed.

- Sanitized result SHA-256: `ddfd371c62f0c4f189aaaa98d6113a7c1bb322bd9ba011c3243b73cd516dab2b`
- Controlled result SHA-256: `63deea111b82b212687cfca82f5ba3259102d38cf8519422b07b80629f7702ad`
- Result: [`m2b_c_task_adjusted_result.json`](../../manifests/m2b_c_task_adjusted_result.json)
- Frozen rules: [`m2b_c_task_adjusted_scoring.json`](../../manifests/m2b_c_task_adjusted_scoring.json)
