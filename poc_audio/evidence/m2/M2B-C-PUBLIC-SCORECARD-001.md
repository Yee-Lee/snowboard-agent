# M2B C ASR public scorecard

Date: 2026-08-22
Status: `BOUNDED SCORECARD READY FOR EXTERNAL CITATION / NOT A POPULATION BENCHMARK`

## Scope and review

C is a product-representative curated set for Snowboard, not a Taiwan Mandarin
population benchmark. It contains 16 controlled Internal items, balanced
across Taiwan Mandarin, code-switch, number/date, and product-term categories,
plus 8 Common Voice 26.0 `zh-TW` CC0-1.0 external-sanity items. Dev/holdout each
contain 12 items; prompt selection used dev before the frozen holdout opened.

User blind-first audio/reference review completed all 24 items: 23 labels were
confirmed and one append-only reference erratum was applied. There were no
remaining review, audio-quality, or speaker-slip findings. The sanitized audit
is [`m2b_c_label_audit_result.json`](../../manifests/m2b_c_label_audit_result.json),
SHA-256 `85e407b4ef9cebf40634a7a2d125e86d679574fccbe7b44e2165067dd9424e96`.

## Frozen recipe

Pi 5 aarch64 CPU-only; whisper.cpp 1.9.2; 16 kHz mono S16_LE; four threads;
`language=zh`; P0 endpoint; greedy `best_of=1`; no context, timestamps, internal
VAD, or added padding; fixed reviewed domain prompt. Exact model, worker,
runtime, prompt, and result hashes are in
[`m2b_c_asr_recipe_proposal.json`](../../manifests/m2b_c_asr_recipe_proposal.json).

## Corrected prompt-profile observations

| Family | Metric | Base Q8 primary | Small Q8 fallback |
| --- | --- | ---: | ---: |
| Internal (16) | Raw CER | 29/191, 15.18% | 23/191, 12.04% |
| Internal (16) | Task-adjusted CER | 22/189, 11.64% | 16/189, 8.47% |
| Internal (16) | Raw exact sentence | 7/16, 43.75% | 9/16, 56.25% |
| Internal (16) | Adjusted exact sentence | 8/16, 50.00% | 11/16, 68.75% |
| Common Voice (8) | Raw CER | 12/87, 13.79% | 10/87, 11.49% |
| Common Voice (8) | Task-adjusted CER | 8/87, 9.20% | 5/87, 5.75% |
| Common Voice (8) | Raw exact sentence | 4/8, 50.00% | 4/8, 50.00% |
| Common Voice (8) | Adjusted exact sentence | 5/8, 62.50% | 5/8, 62.50% |

Task-adjusted scoring is secondary and never overwrites raw output. Bounded
C-v1 accepts only its frozen Traditional/Simplified character mapping, Chinese
integer 0–9999, and percentage equivalence. It accepts no homophone or product
alias correction.

## Pi cost

| Family | Metric | Base Q8 primary | Small Q8 fallback |
| --- | --- | ---: | ---: |
| Internal | Latency p50/p95 | 1.334/1.379 s | 4.130/4.253 s |
| Internal | RTF p50/p95 | 0.459/0.530 | 1.419/1.641 |
| Common Voice | Latency p50/p95 | 1.325/1.335 s | 4.112/4.194 s |
| Common Voice | RTF p50/p95 | 0.329/0.428 | 1.019/1.329 |
| Both | Peak RSS | about 285 MiB | about 574 MiB |
| Both | Model bytes | 81,768,585 | 264,464,607 |

Base Q8 is the proposed primary for current hardware. Small Q8 saves 6 adjusted
Internal edits and 3 adjusted Common Voice edits, but costs about three times
the latency and 289 MiB additional peak RSS.

## Prompt boundary

Against each model's no-prompt baseline, the fixed prompt changes adjusted
Internal edits by -13 (base) and -2 (small), but Common Voice edits by +1 for
both. It is a domain tradeoff, not a universal quality improvement.

## Historical consistency context

The separate immutable `POC-AUDIO-PERF-2026-001` packet ran Small Q8 on 50
Internal fixtures for two hot cycles. It observed latency p50/p95
4.042/4.139 s, RTF p50/p95 1.307/1.933, and peak RSS 555.438 MiB. Its packet,
recipe, and scoring differ, so its quality result is not pooled with C. Its
cost observations independently support C's roughly 4.1 s and 574 MiB Small
Q8 result.

## Citation boundary

An accurate citation must name these exact models, recipe, Pi hardware, curated
set, sample size, scoring rules, and holdout design. It must not shorten the
result to a general claim such as “Taiwan Mandarin CER is 8.47%.” Private audio,
controlled transcripts, hypotheses, and User comments are not published.
