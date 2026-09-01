# Snowboard ASR Product R1 POC

This repository evaluates low-latency, local, streaming ASR pipelines on a
Raspberry Pi 5 using CPU only. It compares official model/runtime pipelines
with the accepted Whisper base-Q8 control and produces one final outcome:
`SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`.

Current status is in [`docs/milestone/README.md`](docs/milestone/README.md).
The contract is in [`docs/handoff/inbound/`](docs/handoff/inbound/), and working
rules are in [`docs/workflow.md`](docs/workflow.md).

The active M1 probe order is Zipformer zh x-large INT8, WeNet WenetSpeech
streaming CTC INT8, Nemotron 3.5 Streaming 0.6B Q8_0, Zipformer zh large INT8,
and WeNet AISHELL streaming CTC INT8. Exact identities are fixed before
execution. The workstation runs the complete non-formal development suite
before critical smoke and lifecycle cases are repeated on Pi 5 CPU-only
hardware. See the
[`M1 research summary`](docs/research/ar1_m1_target_and_feasibility.md).

Human authority lives under `docs/`; source, tests, schemas, manifests, tools,
deliveries, and sanitized evidence live under `asr_r1/`.

The complete predecessor tree remains immutable at `audio_m4` /
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`.
