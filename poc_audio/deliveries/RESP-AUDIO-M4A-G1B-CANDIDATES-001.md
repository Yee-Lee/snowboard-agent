# Audio POC → Core Team: M4a Gate 1B Exact Candidate Proposal

- **Response ID**: `RESP-AUDIO-M4A-G1B-CANDIDATES-001`
- **In response to**: `DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001`
- **Core binding**: branch `dev_agent_m4`, commit
  `e3d25d1fc70d726d5bd3162cdcb9571b30937587`, path
  `docs/outsource/deliveries/DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001.md`
- **POC branch**: `dev_audio_m2`
- **POC proposal commit**: supplied in the direct relay after commit; the tracked
  manifest intentionally keeps `proposal_commit: null`
- **Status**: `PROPOSED / NOT AUTHORIZED — GATE 1B ROW ACK REQUIRED`
- **Prepared**: 2026-08-17
- **Architecture change**: `No`

## 1. Disposition and boundary

Gate 1A is accepted. Audio POC submits the exact candidate-scope proposal below
for Gate 1B review. The machine-readable authority is
[`m4a_gate1b_candidates.json`](../manifests/m4a_gate1b_candidates.json), validated
against
[`gate1b_candidate_proposal.schema.json`](../schemas/gate1b_candidate_proposal.schema.json).
The manifest binds immutable upstream identities, POC-computed source/model/
voice/wheel SHA-256, acquisition time, licenses/notices, declared dependencies,
planned aarch64 recipes, native contracts and controlled locators.

This packet contains no eligibility `PASS`, benchmark or product selection. No
real runtime/model/voice was built, installed, imported, loaded or executed. No
inference, Pi run, HAL integration, quality/resource measurement or User scoring
occurred. Source/model/voice/wheel bytes remain in a Git-ignored controlled area;
only sanitized metadata, policy, schema and artifact-independent validation are
tracked. A `REQUEST_AUTHORIZE` row means only “Core may admit this exact row to
post-ACK build and Gate 2A evaluation.”

This advances final checklist sections 2–4: reproducible identity, offline build
inputs, license traceability and candidate eligibility. It does not close any
M2 quality, resource, lifecycle, Pi or final-delivery item.

## 2. Exact candidate decision request

| Row | Domain / origin | Exact engine + artifact | Requested disposition | Basis |
| --- | --- | --- | --- | --- |
| `vad-silero-onnx-6.2.1` | VAD / Core baseline | Silero `6.2.1` commit `7e30209…`; embedded `silero_vad.onnx` `1a153a2…` | `DEFER` | Model/source exact; Python 3.13 aarch64 onnxruntime wheel closure not exact. |
| `vad-webrtc-2.0.10` | VAD / Core baseline | PyPI sdist `f1bed2f…`; vendored WebRTC C VAD | `AUTHORIZE` | MIT source, no runtime model/dependency, bounded offline source-build proposal. |
| `asr-whispercpp-base-q5_1-1.9.2` | ASR / Core baseline | whisper.cpp `1.9.2` commit `306c88f…`; multilingual base Q5_1 `422f1ae…` | `AUTHORIZE` | MIT CPU-only source path; exact 59,707,625-byte model. Model notice and zh-TW quality remain gates. |
| `asr-vosk-small-cn-0.22` | ASR / Core baseline | Vosk `0.3.45`; aarch64 wheel `54efb47…`; small-cn model `3af8b0e…` | `DEFER` | Engine/model exact; broad Python dependency graph lacks an immutable offline wheel lock. |
| `asr-pocketsphinx-zh-unavailable-5.1.1` | ASR / Core baseline | PocketSphinx `5.1.1`; official model registry snapshot `6569e1d…` | `REJECT` | Bundled model is US English; exact official registry snapshot has no Chinese/zh-TW model set. |
| `asr-sherpa-sensevoice-int8-2025-09-09` | ASR / alternative | sherpa-onnx `1.13.5`; exact two-wheel aarch64 closure; SenseVoice int8 `7305f79…` | `AUTHORIZE` | Runtime closure exact; archive lineage resolves to Apache-2.0 ASLP-lab model revision. |
| `asr-sherpa-paraformer-zh-small-2024-03-09` | ASR / alternative | sherpa-onnx `1.13.5`; Paraformer small int8 `da92b3d…` | `REJECT` | Archive has no LICENSE; exact upstream ModelScope API license fields are blank. |
| `tts-piper-chaowen-medium-1.7.0` | TTS / Core baseline | piper-tts `1.7.0`; Chaowen medium `820d64a…`, config `a6bb2ca…` | `DEFER` | Card claims CC0 dataset but says fine-tuned from non-commercial Xiao Ya; legal lineage unresolved. |
| `tts-espeak-ng-cmn-1.52.0` | TTS / Core baseline | espeak-ng `1.52.0` commit `4870adf…`; embedded `cmn` data | `AUTHORIZE` | Exact copyleft source/data and minimal offline source-build proposal; quality still untested. |
| `tts-coqui-baker-unavailable-0.27.5` | TTS / Core baseline | maintained coqui-tts `0.27.5` source `64304dd…`; no compatible exact Baker artifact | `REJECT` | Core-named Baker archive is from legacy v0.6.1 registry; no immutable compatibility statement binds it to current engine, and the torch closure is open. |
| `tts-sherpa-melo-zh-en-1.13.5` | TTS / alternative | sherpa-onnx `1.13.5`; exact two-wheel aarch64 closure; Melo zh/en `e58351e…` | `AUTHORIZE` | Model archive contains MIT license and declares 44.1 kHz native output. |

Requested Gate 1B authorized rows are therefore exactly:

1. `vad-webrtc-2.0.10`
2. `asr-whispercpp-base-q5_1-1.9.2`
3. `asr-sherpa-sensevoice-int8-2025-09-09`
4. `tts-espeak-ng-cmn-1.52.0`
5. `tts-sherpa-melo-zh-en-1.13.5`

The deferred and rejected rows remain in the manifest so Core can decide them
explicitly and the baseline review has no silent omissions. Core may reject an
authorization request, but must not convert a deferred/rejected identity into a
different model, voice, quantization or dependency set under the same row ID.

## 3. Provenance and artifact handling

All complete proposal artifacts were acquired or materialized between
`2026-08-17T14:45:29Z` and `2026-08-17T15:27:22Z`. Per-file UTC time, HTTPS URL,
immutable revision, filename, byte size, SHA-256, license/notice and logical
controlled locator are recorded in the manifest. Git-generated source snapshots
are deterministic archives of the exact listed commit and say so in `notice`;
PyPI/Hugging Face/GitHub release bytes retain their direct immutable URL.

Controlled policy:

- Physical workstation root: `poc_audio/artifacts/gate1b/`; ignored by Git.
- Portable logical root: `controlled://audio-poc/gate1b/`.
- Tracked policy: [`poc_audio/artifacts/README.md`](../artifacts/README.md).
- Permitted inspection: archive listing/extraction of license, README, package
  metadata and config; hashing and size calculation only.
- Prohibited: build/install/import/load/execute, inference, benchmarks, Pi/HAL,
  User scoring, and Git storage of archives/weights/wheels/`.so`/raw audio.

An interrupted Coqui Baker transfer is named `*.partial` in the ignored area and
is not a proposal artifact, checksum or controlled locator. It must not be used.
Coqui is rejected from this exact scope rather than represented by incomplete
bytes. PocketSphinx’s 407-byte registry snapshot is negative provenance evidence,
not a speech model.

## 4. License and dependency closure

| Family | Engine license | Model/voice disposition | Runtime/build dependency closure |
| --- | --- | --- | --- |
| WebRTC VAD | MIT | No external model | Vendored C source; system compiler/Python headers/setuptools build input, no runtime dependency declared. |
| Silero | MIT | MIT source-embedded ONNX | `onnxruntime>=1.16.1` aarch64/Python 3.13 wheel closure open; deferred. Torch is intentionally excluded from the proposed direct-ONNX wrapper. |
| whisper.cpp | MIT | Model repo MIT notice; upstream model/data notice retained | Vendored ggml CPU build; optional BLAS/GPU/server/RPC/download paths disabled. |
| Vosk | Apache-2.0 | small-cn cataloged Apache-2.0 | Official aarch64 wheel exists; `cffi`, `requests`, `tqdm`, `srt`, `websockets` closure open; deferred. |
| PocketSphinx | BSD-2-Clause | No Chinese/zh-TW artifact | Engine-only dependency metadata recorded; rejected before build. |
| sherpa-onnx | Apache-2.0 | SenseVoice lineage Apache-2.0; Paraformer unknown; Melo archive MIT | Exact runtime closure is `sherpa-onnx==1.13.5` CPython 3.13 aarch64 wheel plus `sherpa-onnx-core==1.13.5` aarch64 wheel; both POC-hashed. |
| Piper | GPL-3.0-or-later | Chaowen derivative lineage ambiguous | `onnxruntime`, `pathvalidate` and zh text dependencies listed but not locked; deferred. |
| espeak-ng | GPL-3.0-or-later plus documented data-component notices | `cmn` data embedded in exact source | Minimal callback/file PCM source build; optional direct playback backends disabled. |
| Coqui | MPL-2.0 | No exact compatible Baker row | Large maintained-engine dependency list recorded; model compatibility, torch/torchaudio and transitive closure open; rejected. |

No license statement is treated as product legal approval. In particular,
acquisition under an open-source label does not resolve model training-data or
derivative restrictions. Core legal review remains the owner for any deferred
voice and for final redistribution notices.

## 5. Planned aarch64 and offline path

Every manifest row binds platform
`Raspberry Pi 5 / Debian 13 / aarch64 / Python 3.13`, status
`NOT_EXECUTED_GATE_1B` and network policy `offline_from_hashed_inputs`. The
per-row recipe is a proposal, not evidence:

- Source candidates build in disposable directories from exact source plus
  pinned system/build inputs; produced binaries/wheels receive new SHA-256 before
  import or execution.
- Wheel candidates install into isolated environments with `pip --no-index` from
  the controlled closure only.
- Models/voices use explicit controlled paths. Runtime download, endpoint,
  credential or cache fallback is forbidden.
- A missing hash, dependency, notice or compatible artifact stops the row before
  build. It is not repaired by reaching the network during installation.

Only after an exact-row Gate 1B ACK may the POC execute these recipes, import a
runtime or load a model. Clean-Pi reproduction, offline inference and P11/P12
remain later evidence and start `Pending`.

## 6. Native contract proposal

All formats below are upstream/config declarations and are explicitly
`DECLARED_UNVERIFIED_GATE_1B`; none was observed by running a candidate.

| Row family | Native input | Native output / adapter consequence |
| --- | --- | --- |
| WebRTC VAD | 16 kHz mono S16_LE, frozen 20 ms / 320 samples | Boolean observation per frame; frozen endpoint state machine remains external. |
| Silero VAD | 16 kHz float32, 512-sample model window | Probability per window; adapter buffers 20 ms S16_LE frames without resampling and cannot change endpoint semantics. |
| ASR rows | Frozen 16 kHz mono S16_LE utterance; float32 only where the engine API declares it | UTF-8 final text scored with frozen zh-TW normalization. Simplified output is a quality risk, not an implicit converter permission. |
| Piper Chaowen | UTF-8 Chinese through exact zh frontend | Declared 22050 Hz mono S16_LE. |
| espeak-ng `cmn` | UTF-8 text, explicit `cmn` voice | Expected callback rate 22050 Hz mono S16_LE; actual initialization rate must be asserted post-ACK. |
| sherpa Melo | UTF-8 zh/en through archive dictionary/FST | Declared 44100 Hz mono S16_LE. |

No TTS or Speak resampler is proposed. A future Gate 2A ACK may record the
finalist’s observed native PCM for artifact-independent interfaces, but only Gate
2B may freeze product configuration. Any mismatch between declaration and
observed PCM is a candidate failure or change request.

## 7. Remaining risk and next action

Final delivery remains `AT_RISK` because this metadata review already removed
PocketSphinx, Paraformer and the proposed current Coqui/Baker combination, while
Silero, Vosk and Piper are not eligible until dependency/legal gaps close.
However, the requested authorized set retains at least one exact path for VAD,
two for ASR and two for TTS, so the final baseline remains reachable without
relaxing frozen quality/resource/lifecycle gates.

After Core returns Gate 1B:

- only rows explicitly accepted by ID and this proposal commit may be built;
- rejected/deferred rows remain provenance-only;
- WP2 may continue artifact-independent fake/protocol work;
- WP3 comparison waits for exact-row authorization, the shared scaffold cut and
  a clean test SHA; and
- P9 remains `Blocked` until the Core-owned surrogate arrives at WP4/S4 entry.

## 8. Requested Core Gate 1B reply

Please issue a separate committed candidate-scope ACK that:

1. cites this response path, `dev_audio_m2` and the relayed full proposal SHA;
2. lists all eleven row IDs as `ACCEPTED`, `REJECTED` or `DEFERRED` without
   substituting same-name artifacts;
3. confirms accepted rows may proceed only to the declared offline build/import/
   isolated Gate 2A work, not production lock or Gate 2B acceptance;
4. resolves whether the Whisper model notice and SenseVoice upstream-license copy
   are sufficient for POC evaluation; and
5. preserves `zh-TW`, no implicit ASR/TTS/Speak resampling, the stricter frozen POC
   gates and the existing P9 delivery point.

Until that ACK is committed and directly delivered, all real candidate build,
install, import, load, execution, benchmark and Pi/HAL work remains blocked.
