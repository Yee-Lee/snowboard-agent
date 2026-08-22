# M2B C base Q8 beam=3 probe

Date: 2026-08-22  
Disposition: `REVIEWED / GREEDY RETAINED / HOLDOUT SEALED`

Eight Internal dev P0 records compared greedy `best_of=1` with beam size 3,
patience 1.0. Both arms used base Q8, four threads, `language=zh`, no prompt,
context, timestamps, or internal VAD. This aligns with the isolated M2X
`D1_BEAM3_ONLY` variables but does not reproduce faster-whisper decoding.

| Decoder | CER | Edits / chars | Sentence correct | Latency p50 | RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Greedy | 17.708333% | 17 / 96 | 37.5% | 1256.283 ms | 267.047 MiB |
| Beam=3 | 17.708333% | 17 / 96 | 25.0% | 1307.180 ms | 295.703 MiB |

Beam=3 has no aggregate CER gain, loses one correct sentence, adds 50.897 ms
p50 latency and 28.656 MiB RSS. It is better than the separate beam=5 profile
by one edit, but neither beam profile improves on greedy, so holdout remains
sealed and base Q8 retains P0+greedy.

All eight reversed-order greedy hypothesis hashes match both prior greedy runs.
The exact Pi SHA was `fd484465728185e09ffa1fd3bdf21d743faa6cd5`;
both workers cleaned up, the network remained isolated, and no audio device was
opened. The sanitized result is
[`m2b_c_base_q8_beam3_result.json`](../../manifests/m2b_c_base_q8_beam3_result.json),
SHA-256 `e08734134d7e847920e8543786b3a88afb1fb5a7f382b1c90011add307500dd8`.
The controlled result SHA-256 is
`815ac608a2f24410107a54fcafec858e81527bf3ea81c8b1420ba951312c03b4`.
