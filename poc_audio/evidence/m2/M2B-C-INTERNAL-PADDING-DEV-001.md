# M2B C Internal padding dev probe

Date: 2026-08-22  
Disposition: `OBSERVATIONS_REVIEWED / P300 PROVISIONALLY ADVANCES TO HOLDOUT`

Base Q8 ran on the eight Internal dev records only. P0, P300, and P500 used the
same source, reference, runtime, decoder, and four-thread worker; only frozen-label
padding changed. Common Voice and Internal holdout remained unexecuted.

| Profile | CER | Edits / chars | Sentence correct | Latency p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| P0 | 17.708333% | 17 / 96 | 37.5% | 1253.128 ms | 266.312 MiB |
| P300 | 16.666667% | 16 / 96 | 37.5% | 1254.977 ms | 266.312 MiB |
| P500 | 17.708333% | 17 / 96 | 25% | 1261.480 ms | 266.312 MiB |

P300 improves the aggregate by one edit, but this is a weak and mixed result: one
number/date item improves by three edits while one product-term item regresses by
two. Its p50 latency increases 1.849 ms. The lower RTF is caused by the longer
audio denominator and is not an efficiency gain. P500 has no aggregate CER benefit
and loses one correct sentence, so it does not advance.

P300 is frozen as the only holdout arm; P0 remains the named baseline. Holdout must
confirm a useful quality delta before P300 can enter a recipe. The run used Pi SHA
`a0483fa479e5821690eb0f3da312f1ef03c9b1b7`, cleaned up fully, opened no audio
device, and had no error. The tracked sanitized result is
[`m2b_c_padding_dev_result.json`](../../manifests/m2b_c_padding_dev_result.json),
SHA-256 `73132c6dcf8c029105ec3ca298b9f4a5234f6cd625c4992d654d0c2cc9d75c90`.
The controlled result SHA-256 is
`f42a9a5e559647b0698e1936abb9f7cae124a8e80f5e742d29e224ffdddbdb5b`.
