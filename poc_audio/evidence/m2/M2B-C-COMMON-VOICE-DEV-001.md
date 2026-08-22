# M2B C Common Voice dev baseline

Date: 2026-08-22  
Disposition: `OBSERVATIONS_REVIEWED / HOLDOUT SEALED`

The four Common Voice dev clips ran as full clips with greedy decoding, no padding,
prompt, or front-end processing. Internal records and Common Voice holdout were not
executed.

| Candidate | CER | Edits / chars | Sentence correct | Latency p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| base Q8 | 31.818182% | 14 / 44 | 0% | 1259.270 ms | 265.984 MiB |
| small Q8 | 20.454545% | 9 / 44 | 25% | 3957.295 ms | 555.641 MiB |

Small Q8 saves five aggregate edits, but six saved edits come from D05 while N03
regresses by one. It costs about 2.70 seconds p50 latency and 289.657 MiB RSS. This
small external dev set supports the established quality/resource trade-off but is
not a final model selection or a reason to open holdout.

The Pi SHA was `722f6a0e938efa837f67c19e82dd567bb40482c6`; both workers
cleaned up, no audio device was opened, and no error occurred. The sanitized result
is [`m2b_c_common_voice_dev_result.json`](../../manifests/m2b_c_common_voice_dev_result.json),
SHA-256 `2552595f91f231206933cc5836b73ae3174aca174d442a54712812fd5293d58f`.
The controlled SHA-256 is
`a465097dfac8517c4ff5f0da88079b19b81ba5c882910f4feaf0ff4d885b5646`.
