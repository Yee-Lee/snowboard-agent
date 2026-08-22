# M2B C Internal padding probe

Date: 2026-08-22  
Disposition: `REVIEWED / NO BASE-Q8 PADDING CHANGE RETAINED`

The frozen base Q8 comparison changed only frozen-label padding. Internal dev
screened P0/P300/P500; P300 alone advanced to the previously sealed holdout.
Common Voice was not executed because it has no frozen VAD bounds.

| Split | P0 CER | P300 CER | P0 edits | P300 edits | Sentence P0 → P300 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dev, 8 | 17.708333% | 16.666667% | 17 | 16 | 37.5% → 37.5% |
| Holdout, 8 | 29.032258% | 30.107527% | 27 | 28 | 0% → 12.5% |
| Combined, 16 | 23.280423% | 23.280423% | 44 | 44 | 18.75% → 25% |

Combined category CER changes were Taiwan Mandarin 6.521739% → 8.695652%,
code-switch unchanged at 23.333333%, number/date 35.714286% → 28.571429%, and
product-term 29.268293% → 34.146341%. P300 therefore redistributes errors rather
than reducing them. Combined median latency was effectively unchanged: 1260.391 ms
versus 1260.440 ms. Lower padded-audio RTF is a denominator effect, not a speedup.

P0 remains the base Q8 recipe. This candidate-specific result does not claim that
padding is universally ineffective. The exact Pi holdout SHA was
`ed9ba86bc8874cfe4f9ae1970f83e23023979d3d`; cleanup was complete, no audio device
was opened, and no error occurred.

- Dev sanitized SHA-256:
  `73132c6dcf8c029105ec3ca298b9f4a5234f6cd625c4992d654d0c2cc9d75c90`
- Holdout sanitized SHA-256:
  `4d336730ded73d2578b2c3bf243bf29434ac58ac847b0accb22d9b84b45b762d`
- Holdout controlled SHA-256:
  `4420e9e276b595ba26496e85a799a0eec95d9e35f175940c5c20a5bdcd0ae887`

Tracked machine results:
[`dev`](../../manifests/m2b_c_padding_dev_result.json) and
[`holdout`](../../manifests/m2b_c_padding_holdout_result.json).
