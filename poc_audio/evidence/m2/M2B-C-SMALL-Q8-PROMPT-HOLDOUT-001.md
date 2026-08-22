# M2B C small Q8 domain-prompt holdout

Date: 2026-08-22  
Disposition: `REVIEWED / RETAIN PROMPT IN SMALL Q8 FALLBACK RECIPE`

The unchanged prompt was compared with no prompt on the same pre-frozen 8
Internal and 4 Common Voice holdout WAVs. No holdout reference contained an
exact prompt term.

| Family / profile | CER | Edits / chars | Sentence correct | p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Internal baseline | 22.580645% | 21 / 93 | 25.0% | 3955.977 ms | 555.422 MiB |
| Internal prompt | 24.731183% | 23 / 93 | 25.0% | 4149.155 ms | 573.922 MiB |
| Common Voice baseline | 6.976744% | 3 / 43 | 50.0% | 3918.097 ms | 555.422 MiB |
| Common Voice prompt | 6.976744% | 3 / 43 | 50.0% | 4088.374 ms | 573.922 MiB |

Holdout alone regresses by 2 Internal edits with no sentence change; Common
Voice text is unchanged and no prompt term is inserted. Across pre-frozen dev
plus holdout, however, prompt reduces small Q8 Internal edits from 31 to 25 and
raises correct sentences from 5/16 to 9/16. This retained aggregate benefit and
zero-insertion evidence support prompt in the fallback recipe, with the holdout
regression explicit.

The exact Pi SHA was `1f23a9623e8a9d45f0fd2f03fc08d9c016dce0ac`;
workers cleaned up, network remained isolated, and no audio device was opened.
The sanitized result is
[`m2b_c_small_q8_prompt_holdout_result.json`](../../manifests/m2b_c_small_q8_prompt_holdout_result.json),
SHA-256 `daff6156d44dcf652d719d050923b91a4446ef5b3a1eee58219176cc5a95279b`.
The controlled result SHA-256 is
`937174e27478e5fb0167050b040c613eeb1c5409e7f226331d9ac5c25829b3bb`.
