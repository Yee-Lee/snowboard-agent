# Core Team → Audio POC Team: M4a Gate 1B ASR Recovery ACK

- **Delivery ID**: `DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002`
- **Related handoff**: `PM-OUT-260819-019-audio-asr-recovery-gate`
- **Related change request**: `CR-AUDIO-M4A-G1B-ASR-SCOPE-001`
- **Supersedes ASR row disposition in**: `DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`
- **Reviewed POC branch / commit**: `audio` / `ccfc2477a04cd2c53341fabb13a620fd89a51e5a`
- **Status**: `ACCEPTED — Q8_0 PRIMARY; Q5_1 CONDITIONAL FALLBACK ONLY`
- **Owner**: Core Team Designer
- **Date**: 2026-08-20
- **Architecture change**: `No`

## 1. Disposition

Core 接受 Audio POC 的 ASR recovery 請求。SenseVoice 依原 frozen fixture 的結果維持
quality rejection，不得重調、改 threshold 或重寫歷史 evidence。本 ACK 只改寫原
Gate 1B ACK 的 ASR 執行列；Matcha TTS 及其他 VAD / ASR / TTS 列的原裁決不變。

| Row | Decision | Execution boundary |
| :--- | :--- | :--- |
| `asr-whispercpp-small-q8_0-1.9.2` | **ACCEPTED — primary** | 通過本 ACK 的 artifact preflight 後才可 build / load / execute；必須先完整跑完 frozen ASR qualification |
| `asr-whispercpp-small-q5_1-1.9.2` | **ACCEPTED — conditional fallback** | 只在 Q8_0 同時通過 CER 與 sentence-correctness gates，但 hot latency p95 `>1.5 s` 或 peak RSS `>1250 MiB` 時可執行 |
| `asr-whispercpp-base-q5_1-1.9.2` | **DEFERRED — non-executable** | 不得將 base row 當作 small fallback |
| faster-whisper `small` CPU `int8` | **DEFERRED — non-executable** | 不在本輪 recovery scope |
| SenseVoice Large / another SenseVoice pass | **REJECTED** | 不得執行 |

Q8_0 若任一 quality gate 失敗，必須保存 failure 並停止；不得執行 Q5_1。Q8_0 若全數通過
hard gates 且未觸發 RSS 條件，也不得為候選比較另跑 Q5_1。

## 2. Pinned source, model artifacts and notices

| Item | Immutable identity | Controlled / upstream locator |
| :--- | :--- | :--- |
| Engine source | whisper.cpp `1.9.2`; Git `306c88f4d1286aec1bf96e544632897886af5501`; archive SHA-256 `988945d81af6abcf52d5e8034f516c74ffc61057c32c3a4b84f3451c2c7e5e47`; 9,613,762 bytes; MIT `LICENSE` | `controlled://audio-poc/gate1b/sources/whisper.cpp-v1.9.2.tar.gz` |
| Q8_0 primary model | `ggerganov/whisper.cpp@5359861c739e955e79d9a303bcbc70fb988958b1`; `ggml-small-q8_0.bin`; SHA-256 `49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f`; 264,464,607 bytes | `controlled://audio-poc/gate1b/models/ggml-small-q8_0.bin` |
| Q5_1 conditional model | same repository revision; `ggml-small-q5_1.bin`; SHA-256 `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`; 190,085,487 bytes | `controlled://audio-poc/gate1b/models/ggml-small-q5_1.bin` |

Model 收件須保留該 immutable revision 的 repository `LICENSE`、whisper.cpp model documentation
與 upstream Whisper model / training-data lineage notice。本 ACK 只授權受控 POC 執行，不等於
final redistribution 或 legal clearance；缺少 notice 仍阻擋 Gate 2B final reference。

## 3. CPU-only aarch64 build closure and preflight

使用上表 exact source archive，限 Raspberry Pi 5 / Debian 13 / aarch64 的 CMake + C/C++
toolchain、`pthread` 與原始碼內 vendored ggml。不得加入 Python runtime、BLAS、CUDA、
Vulkan、OpenCL、RPC、server、FFmpeg、SDL2 或 runtime downloader。最小設定為
`GGML_NATIVE=OFF`, `GGML_BLAS=OFF`, `GGML_CUDA=OFF`, `GGML_VULKAN=OFF`,
`GGML_RPC=OFF`, `WHISPER_CURL=OFF`, `WHISPER_BUILD_SERVER=OFF`,
`WHISPER_COMMON_FFMPEG=OFF`, `WHISPER_SDL2=OFF`。

首次 build / load 前必須 fail closed 驗證：

1. source archive 的 SHA-256、size 與 `LICENSE` 符合上表；
2. 當次 row 的 model filename、exact byte size、SHA-256 與 repository revision 符合上表；
3. configure cache 不含未核准 backend / downloader，build 期間無 network access；
4. 記錄 compiler / CMake / OS / kernel、完整 configure 與 build commands、binary SHA-256 及
   dynamic dependency listing；任一 identity 或 closure 不符即 `Blocked`，不得進 inference。

## 4. Frozen runtime profile and gates

- 四個 CPU threads、單一 worker；greedy decoding（等價 `beam_size=1`, `best_of=1`）；
  `temperature=0`、`language=zh`、translation disabled、previous-text conditioning
  disabled、timestamps disabled、internal VAD disabled。
- 輸入維持 frozen 16 kHz mono bounded utterance；VAD 仍是 ASR 外部獨立 stage。不得以
  resampling、新 normalization、prompting 或 post-processing 變更 frozen score。
- Hard gates：hot final-transcript latency p95 `<=1.5 s`、RTF p95 `<=2.0`、
  Taiwan-Mandarin core CER `<=20%`、overall sentence correctness `>=70%`，以及
  既有 determinism / lifecycle / offline / cleanup gates。Hot latency `<=1.0 s` 仍為
  advisory target；peak RSS `1250 MiB` 為 fallback trigger，不改寫其原 advisory 分級。

## 5. Required return

POC 回交須使用新的 committed candidate SHA，並列出本 ACK ID、row ID、source / model /
binary identity、preflight、完整 commands、frozen fixture / scorer checksum、raw evidence
checksum、每項 gate 結果與 cleanup proof。不得把本 ACK 標記為 Gate 2A `PASS`、final
winner、`POC Accepted` 或 Core product baseline。
