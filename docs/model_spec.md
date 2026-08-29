# Snowboard Runtime Model Baseline

本文件固定產品 runtime model / engine 的 identity、授權與階段 gate。它不保存模型、wheel、native binary、raw audio 或受控結果；實體檔案位於 Git 外，Core 只提交可審查的 provenance / checksum lock。

## 1. 狀態與權威輸入

| 項目 | 固定值 |
| :--- | :--- |
| Audio baseline 狀態 | `FINAL REFERENCE LOCKED — CORE M4A GATE 3 ACCEPTED` |
| Audio delivery ID | `POC-audio-DEL-2026-001-R1` |
| Accepted Audio completion | branch `audio` / tag `audio_m4` / `5694ead4ba6be928fdb4dbdf6da7155b214d72bd` |
| Corrected Gate 2B delivery | `ca51bce9b4e205d9c9faf004d41c27169f108a3f` |
| P9.1 / combined execution | `8be3bc095b504b8eab1dfeb21b94173728b9656f` |
| Failure / recovery execution | `26f33a3c371eee61df46924432839d0fa9ee3bf8` |
| Core HAL execution | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Core intake / approval | `RESP-AUDIO-M4-GATE2B-001` / `be19b70b1dd91674e7ff981eb9d6b2dca9741f54` |

`audio_m4`本身只固定POC reference，不能單獨證明Core Tester PASS；Core M4a已另外以product candidate
`6c3ba95455dc5c2a152aa230b8ae5915887fe6a9`完成inheritance / delta、target acceptance及Designer final
confirmation而Accepted。

## 2. M4a production baseline

### 2.1 VAD / endpoint

| 欄位 | 固定值 |
| :--- | :--- |
| Candidate | `vad-silero-onnx-6.2.1` |
| Source | Silero VAD commit `7e30209a3e901f9842f81b225f3e93d8199902b1` |
| Model | `silero_vad.onnx`, 2,327,524 bytes |
| Model source | `https://raw.githubusercontent.com/snakers4/silero-vad/7e30209a3e901f9842f81b225f3e93d8199902b1/src/silero_vad/data/silero_vad.onnx` |
| Model SHA-256 | `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` |
| Runtime | isolated CPython 3.13 aarch64 venv; `onnxruntime==1.29.0`, `numpy==2.5.2`, `flatbuffers==25.12.19`, `packaging==26.3`, `protobuf==7.36.0` |
| ONNX provider / threads | `CPUExecutionProvider`; intra-op 1, inter-op 1 |
| Input | 16,000 Hz, mono, S16_LE, 320 samples / 640 bytes / 20 ms; adapter converts to float32 windows but does not resample |
| Window / context | 512 samples / 64 official context samples |
| Endpoint profile | positive `0.5`; negative `0.35`; startup mask 160 ms; minimum speech 250 ms; end silence 500 ms; pre/post padding 500/600 ms |
| License | MIT; complete upstream notice required in distribution |

Runtime wheel filenames, sizes and SHA-256 values must be copied exactly from Accepted Audio path `poc_audio/manifests/m2_vad_silero_fallback.json` into the Core product lock. A missing or extra wheel, version mismatch, system-site resolution, model mismatch or non-CPU provider is a startup failure before audio capture.

### 2.2 ASR

| 欄位 | 固定值 |
| :--- | :--- |
| Candidate | `asr-whispercpp-base-q8_0-1.9.2-m2b` |
| Engine | whisper.cpp `1.9.2`, commit `306c88f4d1286aec1bf96e544632897886af5501` |
| Source archive SHA-256 | `988945d81af6abcf52d5e8034f516c74ffc61057c32c3a4b84f3451c2c7e5e47` |
| Product worker baseline SHA-256 | `64ca4ce45899a39afe467e6249a440e3807e18d8e09ff4c3267242d81d2b1b2b`; Core rebuild may change this hash only when the same pinned source/options are recorded as a product delta |
| Model | `ggml-base-q8_0.bin`, 81,768,585 bytes |
| Model SHA-256 | `c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9` |
| Model repository | `ggerganov/whisper.cpp@5359861c739e955e79d9a303bcbc70fb988958b1` |
| Model source | `https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-base-q8_0.bin` |
| Input | bounded 16,000 Hz mono S16_LE utterance from §2.1; no ASR-layer resample |
| Runtime profile | 4 threads; language `zh`; greedy best-of-1; temperature 0; timestamps / translate / internal VAD / previous-text context all disabled |
| Initial prompt SHA-256 | `e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef` |
| License | whisper.cpp, pinned model repository and upstream Whisper: MIT; preserve all three notices; optional GPL/media-codec components are excluded |

The prompt text is product configuration material but must not appear in runtime logs or acceptance result payloads. The worker returns UTF-8 text to the owning adapter; evidence stores only sanitized outcome fields and transcript hash unless a controlled manual card explicitly requires content review.

### 2.3 TTS

| 欄位 | 固定值 |
| :--- | :--- |
| Candidate | `tts-sherpa-matcha-zh-en-1.13.5` |
| Engine | `sherpa-onnx==1.13.5`, source commit `3dc7c569f31ca2cd4a20ed6f7db780327e6714c5` |
| Source SHA-256 | `821a848857d9cb80985841d2197435a3a63f5bc40f7855cd6d958781ed2c31bd` |
| Runtime | isolated CPython 3.13 aarch64 venv containing `sherpa-onnx==1.13.5`, `sherpa-onnx-core==1.13.5` and `numpy==2.5.2` plus allowed bootstrap tooling |
| Wrapper wheel SHA-256 | `f5a6cc5ac96043670faa0f5c0e56310315a4600cf7b764fee014e7dd75fda00f` |
| Native-core wheel SHA-256 | `4cd751063a378a49f0c72eba5ba959fe375397f5baf93a53f3db64097d00e2aa` |
| NumPy wheel SHA-256 | `0aadf13b60048d501e05fa699efaf7734e2494f3498a4c2a5521d822640324f3` |
| Acoustic archive | `matcha-icefall-zh-en.tar.bz2`, 79,033,838 bytes, SHA-256 `271b804af570400d3bcdcb53bf6e53cc9f75180ee763b9f13eb5eaf2b0d086ef` |
| Acoustic source | `https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/matcha-icefall-zh-en.tar.bz2`; lineage cross-check `ModelScope dengcunqin/matcha_tts_zh_en_20251010@f05803ec98df733d5775dfb0c40a919ae699cfb6` |
| Acoustic model | `model-steps-3.onnx`, SHA-256 `524286bf6cf11be74329ae1c682ac69e34d6860c2ea9fd1290319d561540b16a` |
| Vocoder | `vocos-16khz-univ.onnx`, 53,882,848 bytes, SHA-256 `b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e` |
| Vocoder source | `https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos-16khz-univ.onnx` |
| Voice / profile | `matcha-zh-en-default-sid-0`; `sid=0`, speed `1.0`, provider `cpu`, 2 threads, max one sentence |
| Output | native API float samples converted exactly once to 16,000 Hz mono S16_LE; emitted chunks are multiples of one sample and AudioOutput performs the separately accepted 16 kHz mono S16_LE → 48 kHz stereo S32_LE HAL adaptation |
| License | sherpa runtime and pinned Matcha repository: Apache-2.0 |

The acoustic archive includes lexicon, tokens, rule FSTs and `espeak-ng-data`. Before product shipment the notice package must cover runtime, acoustic model, Vocos and all embedded third-party components, retaining Apache-2.0 text, attribution and applicable modification notices.

## 3. Isolation and dependency lock

Core uses three non-overlapping runtime closures:

1. Core controller / Audio HAL environment;
2. VAD environment from §2.1;
3. TTS environment from §2.3.

whisper.cpp is a separately checksum-verified CPU-only native child. Candidate Python/native packages must not be added to `[project.dependencies]` or imported by Core controller modules. Product locks are committed as machine-readable manifests under `requirements/m4a/`; wheel, model, archive and binary payloads remain outside Git. Installation and preflight use only caller-supplied, checksum-matching inputs with network disabled.

Gate 3 canonical command shapes：

```bash
python3 scripts/m4a_audio_product.py build-whisper \
  --lock-root requirements/m4a --source-archive <controlled-source> \
  --build-root <new-staging-dir> --output <new-binary>

python3 scripts/m4a_audio_product.py install \
  --lock-root requirements/m4a --input-root <controlled-inputs> \
  --install-root <new-product-root> --python /usr/bin/python3.13

python3 scripts/m4a_audio_product.py preflight \
  --lock-root requirements/m4a --install-root <product-root> \
  --core-repo <checkout> --core-sha <40-hex-candidate> --config <local-config>
```

`build-whisper`只接受tracked CPU-only CMake option set並記錄product binary SHA-256；`install`先在same-filesystem staging建立隔離VAD/TTS venv、安全展開artifact、驗全部identity後才atomic rename；`preflight`是read-only。三個subcommand都預設network-disabled / no-index，拒絕既存output與未列input，且stdout只輸出sanitized JSON。

The product lock must reject:

- unresolved branch/tag identity or a path selected without a checksum;
- extra/missing wheels, unexpected installed distributions or system-site packages;
- wrong interpreter, architecture, engine/model/voice/profile or optional accelerator;
- artifact directories containing symlink/path traversal or an unpacked component whose checksum differs;
- runtime downloader, network endpoint, credential or fallback to another model.

## 4. Accepted evidence and Core delta

| Area | POC evidence | Core Gate 3 action |
| :--- | :--- | :--- |
| Candidate comparison / license | Accepted completion `5694ead...` and corrected delivery `ca51bce...` | Inherit identity and decision; do not rerun candidate comparison |
| P1 / P4 format | reusable validators / fixed PCM vectors | Rerun through Core ASR/TTS adapters and M3 HAL on product SHA |
| P2 / P3 / P6 quality | Accepted controlled review | Run only bounded semantic/voice smoke to prove the adapter did not change baseline |
| P5 playback | reference sequence only | Rerun real Speak → AudioOutput completion on product SHA |
| P7 / P8 resource | Accepted isolated metrics | Measure Core-owned process tree and latency |
| P9 | P9.1 20/20, 3,339.688 MiB peak under 3,584 MiB | Rerun real M4a + Accepted LLM composition when M4b input is available |
| P10 | 12/12 failure terminals and recoveries | Rerun success/error/timeout/cancel/force-abort/recovery against Core RM/SM |
| P11 | Accepted provenance and closures | Verify product locks, clean install and complete notice inventory |
| P12 | Accepted offline execution | Rerun complete Core product session in disabled network namespace |

Every Core result row must record the Audio delivery ID, Accepted Audio completion SHA, manifest/evidence locator and checksum, product implementation SHA, inheritance reason, delta Test ID/result and acceptance run ID where applicable.

## 5. Accepted risk and change control

The USER owns the remaining unnamed Matcha Chinese/English training-data and voice-lineage risk. This is not a technical Gate 3 blocker. Completing redistribution notices remains mandatory before shipment.

Any change to an engine/model/vocoder/voice checksum, VAD endpoint profile, ASR prompt/decoder, runtime package version, native build option or TTS generation profile is a baseline change. It requires a change request, updated provenance and affected POC/Core delta evidence; it cannot be hidden as a packaging or config-only edit.

Vision and wake-word baselines remain pending their own gates and are not fixed by this Audio section.

## 6. M4b provisional LLM model record（not a production baseline）

### 6.1 Gate 2A decision

| Item | Gate 2A record |
| :--- | :--- |
| Status | `SOLE MODEL FINALIST / INTEGRATION REVISION AND GATE 2B PENDING` |
| Core ACK | `DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001` |
| POC closure | branch `llm` / `3c012eb65cc7c8b706fe1c29a3fcafab17696d0f` |
| Gate 2A execution | `e2b59fac609e0d768ff3554754363900cbed70a9` |
| Execution surface | SHA-256 `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1` |
| Model finalist | `CAND-LRT-G4E2B-MOBILE-R1` / Gemma 4 E2B mobile |
| Rejected formal Gate 2B candidate | `CAND-LRT-Q25-15B-Q8-R1` / Qwen2.5 1.5B Q8 |
| Architecture disposition | `No change`：USER澄清`arch.md`的`Gemma3:e2b`為typo，E2B只存在於Gemma 4；後續正名為Gemma 4 E2B |

User選定的是model finalist，不是current product pairing。R1 machine dispositions保留P2
`FAIL (3/30)`與P8 `FAIL / DEPENDENCY_LIMITED_BY_P2`；P3/P4/P5 PASS。不得把本節當作Gate 2B winner、
production model/dependency lock或M4b Accepted。

### 6.2 Selected reference identity

下列值只供new integration-qualified revision保持model/runtime lineage；Gate 2B final winner前不構成
Core product lock：

| Field | POC reference value |
| :--- | :--- |
| Driver / runtime | `litert_lm` / LiteRT-LM API `0.16.0` |
| Runtime wheel SHA-256 | `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |
| Native library SHA-256 | `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` |
| Model | `gemma-4-E2B-it.litertlm`, 2,588,147,712 bytes |
| Model SHA-256 | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` |
| Model source revision | `litert-community/gemma-4-E2B-it-litert-lm@6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94` |
| Model license | Apache-2.0；final product notice inventory仍待Gate 2B/Core packaging核對 |
| R1 pairing revision | `litert-lm-v0.16.0-pi-r2` |
| R1 product profile | input 128 / output 64 / engine 1024 tokens；temperature 0；top-p 1；threads 4 |
| R1 timeout profile | READY 10s；generate 15s；cancel 500ms；TERM 2s；KILL 1s；rebuild 10s |

### 6.3 Baseline lock conditions

在下列項目全部完成前，`requirements/m4b/`不得出現production lock，factory不得接受real driver作為
shipping baseline：

1. new versioned/frozen Gemma integration revision使用與development cases分離的precommitted或held-out
   catalog完成affected P2/P8 qualification並PASS；
2. replacement Gate 2B packet / lock經review且取得exact-SHA Pi authorization；
3. Accepted Audio package在Pi 5 4GB、`swap=0`完成P9/P10B combined PASS；
4. Core final winner ACK固定driver、runtime/model/product config、artifact checksum與notice inventory；
5. M4B full design review與Tester coverage sign-off完成。

Gate 2B後本節才升格為production baseline，並補齊product lock path、runtime install closure、exact
PromptBuilder/profile checksum、READY identity與POC→Core inheritance locator。任何Gate 2B FAIL或identity
drift都維持pending/no-go，不fallback到Qwen、mock或network service。
