# M2B C small Q8 padding dev probe

Date: 2026-08-22  
Disposition: `REVIEWED / NO HOLDOUT / P0 RETAINED`

Small Q8 ran on the same eight Internal dev records as the base Q8 padding probe.
Only frozen-label padding changed; Internal holdout and Common Voice were not
executed.

| Profile | CER | Edits / chars | Sentence correct | Latency p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| P0 | 10.416667% | 10 / 96 | 37.5% | 3956.048 ms | 555.422 MiB |
| P300 | 12.500000% | 12 / 96 | 37.5% | 3956.012 ms | 555.422 MiB |
| P500 | 15.625000% | 15 / 96 | 37.5% | 3956.635 ms | 555.422 MiB |

P300 adds two code-switch edits. P500 retains those regressions and adds three
product-term edits. Neither arm improves any aggregate sentence outcome, so no
padding arm advances to holdout and P0 remains the small Q8 recipe. Lower padded
RTF is only a longer-audio denominator effect.

The exact Pi SHA was `6e8ad82c484f09a7e2f3838ee1fb3b0151a8c491`; cleanup was
complete, no audio device was opened, and no error occurred. The sanitized result
is [`m2b_c_small_q8_padding_dev_result.json`](../../manifests/m2b_c_small_q8_padding_dev_result.json),
SHA-256 `1bfc956c1d789e7be2e7fcaa93d079653ed90a0d37e88e42aa28e93ca0bf9de9`.
The controlled result SHA-256 is
`d006fd44c07771547a9f312d283041f9c89302458af5bfff51e08bc3f61dc65d`.
