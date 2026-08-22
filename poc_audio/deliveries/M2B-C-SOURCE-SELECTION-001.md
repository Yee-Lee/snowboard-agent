# M2B C source selection

Status: `USER_REVIEWED / PCM LOCKED / NO C INFERENCE`

The reviewed C source set contains 24 items: 16 internal and 8 Common Voice
`zh-TW` 26.0 clips. Dev and holdout contain 12 items each.

- Internal: four Taiwan Mandarin, four code-switch, four number/date, and four
  product-term items.
- Common Voice: four general Mandarin, three number/date, and one Latin-mixed
  item. This is an external sanity subset, not a code-switch benchmark.
- M2A overlap: zero internal fixture IDs and zero Common Voice speakers.
- I18 uses the reviewed spoken reference only for C. Its frozen M1 source-plan
  reference remains unchanged; both reference hashes are retained.
- Controlled audio and plaintext references remain outside Git. Their manifest
  is 24,807 bytes with SHA-256
  `b25b19742b1272a38a0960b276e46aca266fa6ef81d91294e7a70df3aeb96973`.

The sanitized source identity is
[`m2b_c_source_selection.json`](../manifests/m2b_c_source_selection.json).
Pi SHA `23567864c5dc6d5b11f9f9591e167f4f2215e919` produced the reviewed
[`m2b_c_pcm_lock.json`](../manifests/m2b_c_pcm_lock.json): 48 Internal PCM
variants (P0/P300/P500) and 8 full-clip Common Voice PCM files, all 16 kHz mono
S16_LE. The sanitized lock SHA-256 is
`3b748708ee9989223f26429f0c23d06161dc74dc84b83c9b2206bcf248dfb48a`.
Candidate inference remains `NOT_STARTED`.
