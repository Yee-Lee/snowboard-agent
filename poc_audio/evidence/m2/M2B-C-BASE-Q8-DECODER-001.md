# M2B C base Q8 decoder probe

Date: 2026-08-22  
Disposition: `REVIEWED / GREEDY RETAINED / HOLDOUT SEALED`

The eight Internal dev P0 records compared greedy `best_of=1` with beam size 5,
patience 1.0. Both arms used the same newly built worker, base Q8 model, four
threads, language, context, and endpoint controls. Common Voice and Internal
holdout were not executed.

| Decoder | CER | Edits / chars | Sentence correct | Latency p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Greedy | 17.708333% | 17 / 96 | 37.5% | 1253.445 ms | 267.188 MiB |
| Beam | 18.750000% | 18 / 96 | 37.5% | 1359.466 ms | 311.047 MiB |

Beam improves one product-term item by one edit but regresses another by two. It
adds 106.021 ms p50 latency and about 43.859 MiB peak RSS without a sentence gain,
so it does not advance to holdout. Base Q8 retains greedy decoding.

The new worker's greedy hypothesis hashes match all eight predecessor hashes,
proving the decoder-capable worker did not change the named baseline. The exact Pi
execution SHA was `063304fc434242dd7b06528a52f93c541f8e9a3e`; both workers
cleaned up, no audio device was opened, and no error occurred.

The sanitized result is
[`m2b_c_base_q8_decoder_result.json`](../../manifests/m2b_c_base_q8_decoder_result.json),
SHA-256 `4bd9c9a517355aae6a3eecf12e1e528a142b6b9290c005f552bd0c13a42b2ea5`.
The controlled result SHA-256 is
`96231d523727cfbdf5e7a8314551e34676c86e113ac2897bb6efca52f27606ae`.
