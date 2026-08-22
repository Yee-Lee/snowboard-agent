# M2B C base Q8 domain-prompt dev probe

Date: 2026-08-22  
Disposition: `REVIEWED / ADVANCE TO PRE-FROZEN C HOLDOUT`

Base Q8 greedy compared no prompt with one fixed 109-byte domain prompt on the
same 8 Internal and 4 Common Voice dev WAVs. The prompt listed only writing
style and domain terms; it contained no complete test sentence. Both holdouts
remained sealed during this run.

| Family / profile | CER | Edits / chars | Sentence correct | p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Internal baseline | 17.708333% | 17 / 96 | 37.5% | 1262.252 ms | 266.859 MiB |
| Internal prompt | 5.208333% | 5 / 96 | 75.0% | 1325.110 ms | 284.984 MiB |
| Common Voice baseline | 31.818182% | 14 / 44 | 0.0% | 1262.608 ms | 266.859 MiB |
| Common Voice prompt | 13.636364% | 6 / 44 | 50.0% | 1333.547 ms | 285.484 MiB |

The prompt recovered `audio frame`, `音訊基線`, `語音模型`, and `離線執行`;
all five expected domain-term checks passed, with zero Common Voice or Internal
unexpected term insertions. Internal raw CER improved by 12 edits and three
sentences for about 63 ms p50 and 18 MiB RSS.

Common Voice raw improvement is mostly traditional-script selection. Under the
reviewed diagnostic equivalences for simplified/traditional characters and
spoken/written digits, Common Voice changes from about 1 adjusted edit without
prompt to 2 with prompt because L03 adds `館`→`管`; this regression remains
explicit. The same numeric diagnostic treats `十五`→`15` as correct and does not
overwrite raw CER.

All 12 reversed-order baseline hypothesis hashes match their predecessors. The
exact Pi SHA was `f9ba35067587e5ca8246f0302465ddfda488428a`; both workers
cleaned up, the network remained isolated, and no audio device was opened.
The sanitized result is
[`m2b_c_base_q8_prompt_dev_result.json`](../../manifests/m2b_c_base_q8_prompt_dev_result.json),
SHA-256 `33e0e875a976c211015f659714d5c2ad7e23ad064a06a34de3d0876d80c44595`.
The controlled result SHA-256 is
`58a7a570dd0b88d1ca5ba5827f8ef3fe087932c091a8b4c44b75564c1b8b236d`.
