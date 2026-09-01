# AR1M1 Target and Completed Feasibility Research

Status: `PRE-EXECUTION RESEARCH BASELINE / SUPERSEDED FOR EXECUTION STATUS`

Date: 2026-09-01

This document separates the confirmed AR1M1 target and completed metadata
research from work that still requires real model execution. It contains no
score, ranking, hardware disposition, qualification decision, or final product
outcome.

## Confirmed M1 target

M1 must bring up the following five candidates on the workstation in this
User-directed probe order:

1. sherpa-onnx streaming Zipformer zh x-large INT8 2025-06-30.
2. sherpa-onnx WeNet WenetSpeech streaming CTC INT8.
3. NVIDIA Nemotron 3.5 ASR Streaming 0.6B portable Q8_0.
4. sherpa-onnx streaming Zipformer zh large INT8 2025-06-30.
5. sherpa-onnx WeNet AISHELL streaming CTC INT8.

The order controls development cost only. It is not a quality ranking. Each
candidate receives one CPU-only streaming smoke using the same frozen 2.66
second fixture and deterministic 160 ms chunks. Completion requires an exact
artifact load, complete PCM consumption, a non-empty final, clean exit, and
diagnostic model-load time when exposed, decode wall time, RTF, and peak
process-tree RSS.

The approximately 1 GB ASR allowance is recorded as a
1,000,000,000-byte RSS reference. Crossing it is retained as research evidence
and does not terminate or eliminate a POC row. Formal comparison and integrated
product qualification remain Pi 5-only.

## Completed candidate research

| Order | Candidate | Locked metadata | Research conclusion before execution |
| --- | --- | --- | --- |
| 1 | Zipformer zh x-large INT8 | Official 597,755,927-byte archive; sherpa-onnx 1.13.5; x86_64 and aarch64 CPU packages | Lockable for a POC. Approximately 736 MiB of declared inference files makes RSS high risk, but the risk is still worth measuring. |
| 2 | WeNet WenetSpeech streaming CTC INT8 | Exact 133,162,857-byte ONNX and tokens at a fixed repository revision; sherpa-onnx 1.13.5 | Lockable for a POC. This is the official sherpa-onnx online CTC conversion path, not proof that native WeNet U2++ attention rescoring runs. |
| 3 | Nemotron 3.5 Streaming 0.6B Q8_0 | Exact 741,548,352-byte GGUF; NeMo-Speech.cpp 0.1.0 publishes x86_64 and aarch64 CPU archives | Lockable for a POC. RSS is high risk, and only broad `zh-CN` support is listed; M1 cannot establish Taiwan Mandarin quality. Model-license obligations still require review before a product recommendation. |
| 4 | Zipformer zh large INT8 | Official 132,634,597-byte archive; sherpa-onnx 1.13.5 | Lockable for a POC. It has a substantially smaller declared closure than x-large, but Taiwan Mandarin quality remains unproven. |
| 5 | WeNet AISHELL streaming CTC INT8 | Exact 49,618,814-byte ONNX and tokens at a fixed repository revision; sherpa-onnx 1.13.5 | Lockable for a POC. It is the smallest listed model row and has the same CTC-versus-native-U2++ scope boundary as WenetSpeech. |

PengChengStarling is outside this sequence by User decision. Its declared
1,220,027,735-byte unquantized inference closure already exceeds the
approximately 1 GB ASR allowance before runtime overhead. The stopped row is
preserved in the identity manifest.

All exact revisions, filenames, sizes, checksums, source URLs, licenses, and
open conditions are frozen in
`asr_r1/manifests/m1_identity_screening.json`. A lockable row means that a
controlled execution attempt is reproducible; it does not mean the model has
loaded successfully or is feasible on Pi 5.

## Completed fixture research

The selected fixture is `asr-clear-002-p0`, a historical Taiwan Mandarin clear
speech command used only as regression smoke. Its source identity was recovered
from controlled historical storage and the human-reviewed 470–3130 ms speech
interval reproduced the frozen 2.66-second PCM identity exactly. The content is
a nonsensitive device-control request. The transcript and WAV remain outside
Git.

The source and derived WAV checks cover file size, SHA-256, WAV format, frame
count, crop bounds, and duration. The repository command
`python3 -m asr_r1.fixture_preflight` reproduces and verifies the crop from
operator-supplied external paths. No new fixture collection is required for
M1 smoke, and this historically used fixture cannot become final holdout.

## Completed implementation readiness

- Exact candidate and runtime identities are machine-readable and checksum
  bound.
- The smoke method is frozen before results and forbids automatic downloads.
- The runner measures warm decode RTF and peak process-tree RSS and records an
  above-reference flag without a memory kill.
- The sherpa-onnx adapter supports the Zipformer transducer and WeNet online CTC
  rows through external model paths.
- Repository-resource paths are repo-root-relative and fail closed on escape;
  models, runtimes, fixtures, transcripts, and raw results stay outside Git.
- Unit, manifest, relocation, and data-safety coverage exists for the frozen
  pre-result method.

## Execution-status pointer

Real workstation development probes have since exercised all five exact rows.
Their sanitized, explicitly non-formal measurements and engineering breakdown
are maintained in
[`AR1M1 Workstation Development Report`](ar1_m1_workstation_development_report.md).
Those development runs do not establish reviewed clean-SHA evidence, Pi 5
behavior, Taiwan Mandarin quality, a formal comparison, or a qualification
decision. This document remains the pre-execution identity and feasibility
baseline rather than the current execution-status source.
