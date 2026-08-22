# M2B C base Q8 domain-prompt holdout

Date: 2026-08-22  
Disposition: `REVIEWED / RETAIN PROMPT IN BASE Q8 PRIMARY RECIPE`

After reviewed dev evidence, the unchanged 109-byte prompt was compared with
no prompt on the pre-frozen 8 Internal and 4 Common Voice holdout WAVs. None of
the holdout references contained any exact prompt term.

| Family / profile | CER | Edits / chars | Sentence correct | p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Internal baseline | 29.032258% | 27 / 93 | 0.0% | 1262.802 ms | 267.141 MiB |
| Internal prompt | 27.956989% | 26 / 93 | 12.5% | 1333.562 ms | 285.016 MiB |
| Common Voice baseline | 13.953488% | 6 / 43 | 50.0% | 1247.305 ms | 267.141 MiB |
| Common Voice prompt | 13.953488% | 6 / 43 | 50.0% | 1316.105 ms | 285.016 MiB |

No prompt term was inserted in any holdout result. Common Voice hypotheses were
unchanged except punctuation. Internal product-term items improve by 3 edits
and one correct sentence, while one Taiwan-Mandarin item regresses by 2 edits;
the net gain is 1 edit. The prompt therefore remains a domain-specific tradeoff,
not a general recognition improvement. It adds about 71 ms p50 and 18 MiB RSS.

The exact Pi SHA was `2c1bcc6df8078973df9b15c2611a868ef5d81e16`;
both workers cleaned up, the network remained isolated, and no audio device was
opened. The sanitized result is
[`m2b_c_base_q8_prompt_holdout_result.json`](../../manifests/m2b_c_base_q8_prompt_holdout_result.json),
SHA-256 `cd04bde138ae030abdb9f70c078b5d264f6403f0e1ff25d234abd3905ce82169`.
The controlled result SHA-256 is
`e98df81ad5d1cd59b9f01c27ad2c6a030728fbcf0ea29517d708f85902a2fe0a`.
