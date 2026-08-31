# Snowboard ASR Product R1 POC

This repository evaluates low-latency, local, streaming ASR pipelines on a
Raspberry Pi 5 using CPU only. It compares official model/runtime pipelines
with the accepted Whisper base-Q8 control and produces one final outcome:
`SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`.

Current status is in [`docs/milestone/README.md`](docs/milestone/README.md).
The contract is in [`docs/handoff/inbound/`](docs/handoff/inbound/), and working
rules are in [`docs/workflow.md`](docs/workflow.md).

Initial candidates are the 2025 Chinese Streaming Zipformer RNN-T,
PengChengStarling Multilingual Zipformer RNN-T, and WeNet U2++ Conformer. Exact
identities are fixed before execution. Official runtimes and artifacts are
evaluated first on Pi 5 CPU-only hardware.

Human authority lives under `docs/`; source, tests, schemas, manifests, tools,
deliveries, and sanitized evidence live under `asr_r1/`.

The complete predecessor tree remains immutable at `audio_m4` /
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`.
