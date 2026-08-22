# M2B C ASR primary/fallback proposal

Date: 2026-08-22  
Status: `READY FOR CORE/USER COMPARATIVE REVIEW / NOT PRODUCTION LOCK`

Both recipes use P0, greedy, four threads, `language=zh`, no context/timestamps/
internal VAD, and the reviewed fixed domain prompt. Raw CER is preserved beside
formal bounded C-v1 task-adjusted scoring; neither changes runtime output.

| Combined C prompt profile | Base Q8 primary | Small Q8 fallback | Fallback delta |
| --- | ---: | ---: | ---: |
| Internal raw CER | 31/189, 16.40% | 25/189, 13.23% | -6 edits |
| Internal adjusted CER | 24/187, 12.83% | 18/187, 9.63% | -6 edits |
| Internal adjusted correct | 8/16, 50% | 11/16, 68.75% | +3 sentences |
| Internal latency p50/p95 | 1.334/1.379 s | 4.130/4.253 s | +2.796/+2.874 s |
| Common Voice raw CER | 12/87, 13.79% | 10/87, 11.49% | -2 edits |
| Common Voice adjusted CER | 8/87, 9.20% | 5/87, 5.75% | -3 edits |
| Common Voice adjusted correct | 5/8, 62.5% | 5/8, 62.5% | none |
| Peak RSS | about 285 MiB | about 574 MiB | about +289 MiB |

Internal adjusted reference length is 187 rather than raw 189 because numeric
canonicalization changes percentage-expression length; Common Voice remains 87.
Against each model's baseline, the prompt changes adjusted Internal edits by
-13 (base) and -2 (small), but Common Voice by +1 for both. It is therefore a
domain tradeoff, not a universal quality gain. Zero listed-domain-term
insertions and all item regressions remain recorded.

Base Q8 is proposed as primary because small saves only 6 Internal and 2 Common
Voice raw edits while taking about three times the latency and twice the RSS.
Small Q8 remains the quality-priority fallback. Exact artifacts, prompt/runtime
checksums, recipes, source evidence, deltas, and scoring boundary are frozen in
[`m2b_c_asr_recipe_proposal.json`](../../manifests/m2b_c_asr_recipe_proposal.json).
Task rules, Pi execution identity, and all raw-to-adjusted aggregates are in
[`M2B-C-TASK-ADJUSTED-001`](M2B-C-TASK-ADJUSTED-001.md).
