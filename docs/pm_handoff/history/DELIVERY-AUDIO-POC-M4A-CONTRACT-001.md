# Core Team → PM → Audio POC Team: M4a Audio POC Contract

- **Delivery ID**: `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`
- **Finding ID**: `OUT-M4A-2026-001`
- **References**: `PM-OUT-260814-010-m4a-audio-poc-contract-gate`、`DELIVERY-AUDIO-POC-M3-ACK-002`、`DELIVERY-AUDIO-POC-M3-VALIDATION-001`、`docs/milestones/M4.md §6.1–6.2`
- **Status**: `READY FOR PM RELAY — PENDING POC INTAKE SHA`
- **Contract owner**: Core Team Designer
- **Relay owner**: PM (轉交 Audio POC Team)
- **Date**: 2026-08-14
- **Architecture change**: `No`

---

## 1. 背景與授權邊界

M3 Audio 以 `DELIVERY-AUDIO-POC-M3-ACK-002` 確立 Option A 產品方向（HAL 內顯式 48→16 kHz conversion）；P1 維持 `FAIL`、P2 為 `PASS`；P4 implementation gate（`DELIVERY-AUDIO-POC-M3-VALIDATION-001`）尚待 POC 回交完整 source SHA。

M4a Audio 是以 M3 Accepted Audio HAL contract 為基礎，在 Core production code 中實作真實 ASR 與 TTS adapter。Audio POC Team 的責任是技術探索、candidate 驗證與 evidence 提交；Core 保留 dependency selection、design acceptance 與 final ACK 決定權。

**在本 contract 各 gate 取得 Core final ACK 前：**

- Audio POC repository 所有 M2 ~ M4 工作只可標示 `Proposed` / `Not authorized`。
- 不得以 POC 自排 roadmap、口頭結果或 branch HEAD 取代 Core 核准的 contract 或 gate evidence。
- Developer 不得引用候選名稱或 POC branch HEAD 解除 Blocked，不得加入 production dependency lock 或開始 real ASR / TTS backend。

既有 M3 條件澄清：
- P1 維持 `FAIL`（target hardware 不得改寫為 native 支援 16 kHz / mono / S16_LE）
- P2 為 `PASS`（device / config / wiring evidence 已通過）
- P4 為 M3 Option A implementation gate（尚待 POC P4-A01 ~ A10 evidence 回交）
- P3（ASR / TTS winner）為 M4a 候選選型輸出，不得以 POC 自排 roadmap 預先視為已授權或已完成

---

## 2. 目標

在 Raspberry Pi 5 + `googlevoicehat-soundcard` 環境，以 M3 Accepted Audio HAL 為輸入，確認並固定：

1. **ASR**：接受 `AudioInput.frames()` 標準 20 ms / 320-sample / 640-byte S16_LE 串流，產生非空 text result；固定 engine、model、版本、授權、checksum 與 Pi 安裝方式。
2. **TTS**：接受固定文字，產生格式正確（`audio.output.stream_format`）的 TTS PCM，完成播放；固定 engine、voice、版本、授權、checksum 與 Pi 安裝方式。
3. **Resource budget**：M4a（ASR + TTS）與 M4b（LiteRT-LM）同時常駐時，符合 target-device Pi 5 資源與 thermal budget；CPU、RSS、throttling 均須有 evidence。

---

## 3. 候選比較基準（Comparison Baseline）

| 域 | 起始候選 | 說明 |
| :--- | :--- | :--- |
| ASR engine | Whisper.cpp (ggml)、Vosk、PocketSphinx | 可提出替代；每個候選須提供 exact version、source SHA-256、transitive deps、license |
| TTS engine | Piper、espeak-ng、Coqui TTS | 同上 |
| 語言 / voice | zh-TW 或 en 依 User / PM 確認 | POC 先以 en fallback；語言產品決策由 PM relay 後確認 |
| Pi 安裝模式 | pip wheel / source build / system package | 不得提交 binary、wheel 或 `.so` 進 Core Git |

每個候選都須與 M3 Audio HAL stream contract 對齊（16 kHz / mono / S16_LE / 320-sample frames）；不得在 ASR / TTS / Speak 層隱式 resample 或格式轉換。

---

## 4. Gate 架構與逐 gate 責任

### Gate 0 ── M3 P4 Final Selection（前置相依）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Audio POC 依 `DELIVERY-AUDIO-POC-M3-VALIDATION-001` 回交完整 40-character source SHA 與 P4-A01 ~ A10 evidence |
| Exit | Core Designer 發出 M3 P4 final selection ACK，明列核准 binding / resampler / valid-bit / buffering / async I/O |
| Owner | POC 執行；Core Designer 決定 |
| Blocking scope | 未取得 final selection ACK 前，Developer 不得開始 Audio real backend，M4a 不得視為已授權 |
| 下一動作 | Core Designer 審核 POC P4 evidence 後發出 ACK；M3 P4 解除後才觸發 Gate 1 |

### Gate 1 ── M4a Candidate Proposal（POC 提出候選清單）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 0 已取得 Core ACK；POC 在本合約目錄下提出 ASR / TTS candidate list，含 exact version、source archive SHA-256、transitive deps、license / notice、Pi build steps |
| Exit | Core Designer 書面確認 candidate list 符合授權範圍，同意 POC 進行 Gate 2 驗證 |
| Owner | POC 提交；Core Designer 核准範圍 |
| Blocking scope | 未取得 Core 書面確認前，不得視為候選已授權；不得開始 benchmark 或在 Core production code 引用 |
| 下一動作 | POC 回交 candidate list（manifest + license table）；Core Designer 在 5 個工作日內回覆 |

### Gate 2 ── M4a 功能 / 品質 / 資源驗證（POC 執行）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 1 已取得候選授權；POC 依 §5 驗證清單對核准候選組合執行全套驗證 |
| Exit | POC 回交完整 40-character source SHA + manifest（含每個 Test ID 狀態）；Core Designer 確認 evidence 完整可重現，發出 Gate 2 ACK |
| Owner | POC 執行；Core Designer 審核；PM 轉達 ACK 通知 |
| Blocking scope | 未取得 Gate 2 ACK 前，Developer 不得加入 ASR / TTS production dependency lock、model 或 adapter 實作 |
| 下一動作 | Core Designer 審核後另發 final winner ACK（見 §7）；必要時要求補交 evidence 或替換候選重跑本 gate |

### Gate 3 ── M4a Core Production Implementation（Developer 實作，Core 內部 gate）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 2 final winner ACK 已發出；`model_spec.md` 已固定 ASR / TTS baseline（engine、model、voice、版本、license、checksum、Pi 安裝方式、benchmark evidence） |
| Exit | Core Tester 對產品 delivery exact SHA 完成 M4a 驗收（`M4A-*` test cases）；Designer 最終 Code Review 無 Blocking finding |
| Owner | Developer 實作；Tester 驗收；Designer 最終審查 |
| Blocking scope | M4a 未 Accepted 前，M4c 不得啟動；M4a + M4b 未同時 Accepted 前，M4 不得宣告 Accepted |
| 下一動作 | Developer 取得 Gate 2 ACK 後建立工作包；不在本 contract 範圍 |

---

## 5. M4a 驗證清單（POC 在 Gate 2 執行）

| ID | 驗證項目 | Required evidence / result |
| :--- | :--- | :--- |
| **M4A-P1** | ASR stream 輸入格式對齊 | 以 M3 HAL 標準 320-sample / 640-byte / 20 ms S16_LE frame 作為 ASR 輸入；不得在 ASR 層 resample；記錄 engine 收到的 actual format |
| **M4A-P2** | ASR result 非空 | 固定 WAV fixture（speech content 已知）可產生非空文字 result；記錄 WER 基準（若可計算）；不要求準確率門檻，但須可重現 |
| **M4A-P3** | ASR 品質門檻 | 靜音 fixture → 無誤觸發；標準語速 fixture → result 非空、無亂碼；記錄 RTF（real-time factor），P95 RTF ≤ 2.0 |
| **M4A-P4** | TTS 輸出格式對齊 | 固定文字輸入，產生 PCM 符合 `audio.output.stream_format`（與 M3 AudioOutput HAL native format 一致，不得隱式轉換）；記錄 actual format |
| **M4A-P5** | TTS 播放完成 | TTS PCM 送入 M3 AudioOutput / Speak path 後播放完整不截斷；記錄 playback duration vs. text length 關係 |
| **M4A-P6** | TTS 品質門檻 | 固定文字可產生清晰可理解語音；人工評分（mean opinion）≥ 3.5 / 5；記錄 voice / model 版本與 evidence path |
| **M4A-P7** | Pi 資源（ASR only） | 10 warm-up 後保存 ASR inference CPU、RSS、P50 / P95 latency raw samples；temperature 與 throttling；Core 依數據核准，不可只寫「可接受」 |
| **M4A-P8** | Pi 資源（TTS only） | 同上，針對 TTS synthesis phase |
| **M4A-P9** | 同時常駐資源（M4a + M4b 模擬） | 同時跑 ASR warm-loop 與 LiteRT-LM stub（或已有 M4b candidate）；記錄 CPU、RSS 峰值、temperature；CPU 溫度 < 80°C 持續 10 分鐘 |
| **M4A-P10** | Lifecycle | ASR / TTS engine init、warm-up、inference、shutdown 各至少 5 次；無 process / thread / fd 殘留；不得在 worker 內保留隱藏 session history |
| **M4A-P11** | Build / license | 從 clean Pi target 依文件可 build / install / rerun；列 OS、kernel、Python、ALSA、package 與 native library 版本；binary / wheel / `.so` 不得提交 Core Git；license / notice 逐項列出 |
| **M4A-P12** | Offline 驗證 | 所有 ASR / TTS inference 在 Pi 無網路環境可完整執行；log 不含 network call、external API endpoint 或 credential |

---

## 6. 必要回交結構

POC repository 回交至少包含下列可定位內容；manifest 中的 relative path 必須完整：

```text
poc_audio/
├── deliveries/
│   └── DELIVERY-AUDIO-POC-M4A-VALIDATION-001.md
├── tools/
│   └── <reproducible M4a runner: ASR + TTS>
├── harness/
│   └── <WAV fixture + text fixture generator>
└── evidence/m4a/
    ├── manifest.json
    ├── environment.txt
    ├── config.sanitized.*
    ├── results.*
    └── raw/
```

`manifest.json` 至少列：POC full SHA、hardware / wiring、sanitized config SHA-256、runner 與 fixture SHA-256、candidate source hashes、license、每個 M4A Test ID 狀態、raw artifact path、開始 / 結束時間與完整 reproduction command。未執行為 `Pending`，硬體或環境不足為 `Blocked`；不得標成 `Pass`。

---

## 7. Winner / No-Go 決定表（POC Gate 2 回交時逐項填寫）

| Decision item | Required answer |
| :--- | :--- |
| ASR engine | selected candidate、version、source SHA-256、license、理由與 rejected alternatives |
| ASR model | model file name、SHA-256、source URL / archive、license、Pi install command |
| TTS engine | selected candidate、version、source SHA-256、license、理由與 rejected alternatives |
| TTS voice / model | voice name、SHA-256、source URL / archive、license |
| 語言設定 | zh-TW / en / other；依 PM relay 確認的產品語言 |
| Stream format alignment | ASR 與 TTS 各自實際輸入 / 輸出 format（sample rate / channels / dtype / frame size） |
| Pi resource summary | P50 / P95 ASR latency、P50 / P95 TTS synthesis latency、peak CPU、peak RSS、thermal peak |
| Offline confirmation | 是否可在無網路 Pi 5 完整執行；log 是否無 credential / API endpoint |
| Residual risk | 已知限制、未通過項目、是否仍可達成 M4a contract；No-Go 條件說明 |

如任何 candidate 無法達成 M4A-P3 / P6 / P9 / P12 任一項，POC 須記錄可重現的 failure 並提出替代；不得宣告 Winner。

---

## 8. 溝通順序（Contract relay flow）

```
Core Designer (contract owner)
  → [本 delivery] PM 正式轉交 Audio POC Team (relay owner)
    → POC Gate 1 回交 candidate list
      → Core Designer 書面確認 Gate 1 (存於 deliveries/)
        → POC Gate 2 執行驗證，回交 exact 40-char source SHA + manifest
          → Core Designer 審核 → final winner ACK (或要求補交)
            → PM 通知 Audio POC Team ACK 結果
              → Developer 取得 Gate 2 final winner ACK → 建立 M4a 工作包
```

每個步驟的 ACK 均由 Core Designer 書面發出，存放於 `docs/outsource/deliveries/`；PM 只負責轉交，不代替 Core 簽發 ACK，也不代替 Audio POC Team 宣告 gate 通過。Audio POC Team 以自己 repo 完整 SHA 與 manifest 回交；不得以 branch HEAD 或部分 evidence 替代。

---

## 9. 本 contract 阻擋範圍摘要

| 阻擋項目 | 解除條件 |
| :--- | :--- |
| Audio POC M2 ~ M4 任何工作視為已授權 | Gate 1 Core 書面確認後（限授權候選範圍） |
| Developer 加入 ASR / TTS production dependency lock | Gate 2 final winner ACK 後 |
| Developer 開始 ASR / TTS model / adapter 實作 | Gate 2 final winner ACK 後 |
| M4a 視為 Accepted | Gate 3：Core Tester 對 delivery exact SHA 驗收 PASS |
| M4c 啟動 | M4a + M4b 均取得 Tester 驗收 PASS（同一 delivery SHA） |
| M4 宣告 Accepted | M4a + M4b + M4c 同一 delivery SHA 全數 Tester PASS |
