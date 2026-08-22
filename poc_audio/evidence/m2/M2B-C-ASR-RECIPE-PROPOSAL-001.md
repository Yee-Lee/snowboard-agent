# M2B C ASR primary/fallback proposal

Date: 2026-08-22  
Status: `READY FOR CORE/USER COMPARATIVE REVIEW / NOT PRODUCTION LOCK`

Both recipes use P0, greedy, four threads, `language=zh`, no context/timestamps/
internal VAD, and the reviewed fixed domain prompt. Raw CER is preserved;
numeric-value and simplified/traditional equivalence remain separate task
diagnostics and do not silently rewrite ASR output.

| Combined C | Base Q8 primary | Small Q8 fallback | Fallback delta |
| --- | ---: | ---: | ---: |
| Internal CER | 31/189, 16.40% | 25/189, 13.23% | -6 edits |
| Internal correct sentences | 7/16, 43.75% | 9/16, 56.25% | +2 sentences |
| Internal latency p50/p95 | 1.334/1.379 s | 4.130/4.253 s | +2.796/+2.874 s |
| Common Voice CER | 12/87, 13.79% | 10/87, 11.49% | -2 edits |
| Common Voice correct sentences | 4/8, 50% | 4/8, 50% | none |
| Peak RSS | about 285 MiB | about 574 MiB | about +289 MiB |

The prompt produced zero listed-domain-term insertions across all dev and
holdout records. It materially recovered reviewed product/code-switch terms on
dev, but is not universally beneficial: base has one general-Mandarin holdout
regression and small has a net 2-edit Internal holdout regression. Those results
are retained; aggregate gains do not erase them.

Base Q8 is proposed as primary because small saves only 6 Internal and 2 Common
Voice raw edits while taking about three times the latency and twice the RSS.
Small Q8 remains the quality-priority fallback. Exact artifacts, prompt/runtime
checksums, recipes, source evidence, deltas, and scoring boundary are frozen in
[`m2b_c_asr_recipe_proposal.json`](../../manifests/m2b_c_asr_recipe_proposal.json).
