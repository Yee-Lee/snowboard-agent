# M2B C small Q8 domain-prompt dev probe

Date: 2026-08-22  
Disposition: `REVIEWED / ADVANCE TO PRE-FROZEN C HOLDOUT`

Small Q8 greedy compared no prompt with the same reviewed 109-byte domain
prompt on 8 Internal and 4 Common Voice dev WAVs.

| Family / profile | CER | Edits / chars | Sentence correct | p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Internal baseline | 10.416667% | 10 / 96 | 37.5% | 3960.708 ms | 554.922 MiB |
| Internal prompt | 2.083333% | 2 / 96 | 87.5% | 4127.601 ms | 573.922 MiB |
| Common Voice baseline | 20.454545% | 9 / 44 | 25.0% | 3961.559 ms | 554.922 MiB |
| Common Voice prompt | 15.909091% | 7 / 44 | 50.0% | 4127.083 ms | 573.922 MiB |

All five expected domain terms were recovered with no unexpected insertion.
The only remaining Internal raw error is semantic-equivalent `十五`→`15`; the
reviewed numeric diagnostic therefore observes 8/8 task-correct Internal items.
The prompt adds about 167 ms p50 and 19 MiB RSS. Common Voice retains the known
L03 regression, so raw script gains are not treated as universal improvement.

The first operator command used a nonexistent model path and stopped before
model load, work-directory creation, inference, or result emission. The frozen
packet was unchanged; the rerun used the checksum-pinned existing model path.

All 12 no-prompt hypothesis hashes match their predecessors. The exact Pi SHA
was `106069b15877169502113f4cb10a5bca0b32f498`; workers cleaned up,
network remained isolated, and no audio device was opened. The sanitized result
is [`m2b_c_small_q8_prompt_dev_result.json`](../../manifests/m2b_c_small_q8_prompt_dev_result.json),
SHA-256 `b81dfc8187968fd8247eb3a57379d3f49766074fe1b7e58e67f3d1e0cf6a1a22`.
The controlled result SHA-256 is
`197a46687ea8c501ac6a13d5966d73db2fa2dea4b9bb841a760e925d76aa0087`.
