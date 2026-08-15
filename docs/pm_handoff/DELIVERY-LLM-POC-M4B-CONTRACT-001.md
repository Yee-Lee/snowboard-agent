# Core Team → PM → LLM POC Team: M4b LLM POC Contract

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Finding ID**: `OUT-M4B-2026-001`
- **References**: `PM-OUT-260814-011-m4b-llm-poc-contract-gate`、`PM-OUT-260805-002-m3-m4-poc-planning`、`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`、`docs/milestones/M4.md §6.1–6.2`
- **Status**: `READY FOR PM RELAY — PENDING POC INTAKE SHA`
- **Contract owner**: Core Team Designer
- **Relay owner**: PM (轉交 LLM POC Team)
- **Date**: 2026-08-15
- **Architecture change**: `No`

---

## 1. 背景與授權邊界

M4b Local LLM 是以 Core production 架構中的 Resource Manager、Reasoner 與 `docs/protocol.md` 為基礎，整合真實本機 LLM 推論引擎（如 LiteRT-LM / MediaPipe LLM 或其他核准候選）。LLM POC Team 的責任是技術探索、候選評估、persistent child reference wrapper 實作、Pi 5 驗證與 evidence 提交；Core 保留 model baseline 定案、protocol 契約審核、整合驗收與 final ACK 決定權。

**在本 contract 各 gate 取得 Core final ACK 前：**

- LLM POC repository 所有工作只可標示 `Proposed` / `Not authorized`。
- 不得以 POC 自排 roadmap、口頭結果或 branch HEAD 取代 Core 核准的 contract 或 gate evidence。
- Developer 不得引用候選名稱或 POC branch HEAD 解除 Blocked，不得加入 production dependency lock 或開始 real LLM backend。
- 外部 LLM 指引（如 `poc_llm/handoff/20260805-1032-llm-poc-guidance/`）僅供參考，不得視為已授權或已 Accepted 輸入。

---

## 2. 目標

在 Raspberry Pi 5（8GB / 4GB）環境，完成 LLM 推論引擎與 persistent child process 驗證，確認並固定：

1. **Runtime & Model**：確認可離線運行的本機推論引擎（如 LiteRT-LM）、Model 架構、Quantization 格式、版本、授權、checksum 與 Pi 安裝方式。
2. **Persistent Child Protocol**：驗證子行程常駐架構，支援 READY handshake、單 turn generate / result、timeout、cooperative cancel、force abort（SIGTERM/SIGKILL + waitpid proof）、recovery barrier 與 history isolation（單 turn 獨立，無跨 session 狀態殘留）。
3. **Resource & Thermal Budget**：M4b（LLM）與 M4a（ASR + TTS）同時常駐時，符合 target-device Pi 5 資源與散熱限制；Peak RSS、CPU 溫度 < 80°C、無 thermal throttling。

---

## 3. 候選比較基準（Comparison Baseline）

| 域 | 起始候選 | 說明 |
| :--- | :--- | :--- |
| LLM Engine / Runtime | LiteRT-LM (TFLite / MediaPipe LLM)、llama.cpp (可提替代) | 每個候選須提供 exact version、source SHA-256、transitive deps、license |
| Model 候選 | Gemma-2-2B-IT、Qwen2.5-1.5B/3B-Instruct、SmolLM2-1.7B-Instruct | 參數量 ≤ 3B，優先以 1.5B ~ 2B 為主，確保 Pi 5 資源餘裕 |
| Quantization | INT4、INT8、GGUF (Q4_K_M / Q8_0) | 須提供 quantization 工具、參數與 quantized artifact SHA-256 |
| Prompt & Format | zh-TW / en System Prompt + JSON intent output | 評估 intent 抽取準確率與 output formatting 穩定度 |
| Target 平台 | Ubuntu (初篩) → Raspberry Pi 5 (8GB / 4GB, 最終 Gate) | 不得提交 binary、wheel、model weights 或 `.so` 進 Core Git |

---

## 4. Gate 架構與逐 gate 責任

### Gate 0 ── LLM POC Contract Receipt & Scope Confirmation（合約接收與環境確認）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | PM 將本 contract 正式交付 LLM POC Team |
| Exit | LLM POC Team 提供 receipt 確認已閱讀本 contract，回交 POC repo 路徑與 initial manifest |
| Owner | PM 轉交；LLM POC Team receipt 確認；Core Designer 記錄 |
| Blocking scope | 未完成 Gate 0 前，LLM POC 探索工作不具備正式合約授權 |
| 下一動作 | POC 準備 Gate 1 candidate proposal |

### Gate 1 ── M4b Candidate Proposal & Ubuntu Pre-screening（候選提案與初篩）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 0 完成；POC 提出 LLM runtime / model / quantization candidate 清單，含 exact version、source archive SHA-256、license、Ubuntu x86/arm64 初篩 benchmark |
| Exit | Core Designer 書面確認 candidate 清單符合授權與產品邊界，同意進入 Pi 5 驗證 |
| Owner | POC 提交；Core Designer 核准範圍 |
| Blocking scope | 未取得 Core 書面確認前，不得將候選視為已核准，不得在 Core production 引用 |
| 下一動作 | POC 回交 candidate list（manifest + license table）；Core Designer 在 5 個工作日內回覆 |

### Gate 2 ── M4b Pi 5 驗證 / Benchmark / Persistent-Child 契約（POC 執行）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 1 已取得候選授權；POC 依 §5 驗證清單對核准候選組合在 Pi 5 執行全套驗證 |
| Exit | POC 回交完整 40-character source SHA + manifest（含每個 Test ID 狀態）；Core Designer 確認 evidence 完整可重現，發出 Gate 2 ACK |
| Owner | POC 執行；Core Designer 審核；PM 轉達 ACK 通知 |
| Blocking scope | 未取得 Gate 2 ACK 前，Developer 不得加入 LLM production dependency lock、model weights 或 child wrapper 實作 |
| 下一動作 | Core Designer 審核後另發 final winner ACK（見 §7）；必要時要求補交 evidence 或替換候選重跑本 gate |

### Gate 3 ── M4b Core Production Implementation（Developer 實作，Core 內部 gate）

| 欄位 | 內容 |
| :--- | :--- |
| Entry | Gate 2 final winner ACK 已發出；`model_spec.md` 已固定 LiteRT-LM baseline；`docs/protocol.md` 已 review 完成 |
| Exit | Core Tester 對產品 delivery exact SHA 完成 M4b 驗收（`M4B-*` test cases）；Designer 最終 Code Review 無 Blocking finding |
| Owner | Developer 實作；Tester 驗收；Designer 最終審查 |
| Blocking scope | M4b 未 Accepted 前，M4c 不得啟動；M4a + M4b 未同時 Accepted 前，M4 不得宣告 Accepted |
| 下一動作 | Developer 取得 Gate 2 ACK 後建立工作包；不在本 contract 範圍 |

---

## 5. M4b 驗證清單（POC 在 Gate 2 執行）

| ID | 驗證項目 | Required evidence / result |
| :--- | :--- | :--- |
| **M4B-P1** | Persistent Child Lifecycle | Child process 啟動、READY handshake 於 10s 內完成；stdin/stdout JSON-lines framing 正常；clean shutdown 無 process 殘留 |
| **M4B-P2** | Single-turn Inference & Result | 固定 text prompt 輸入，可穩定產生非空 response；支援 structured JSON / intent output 格式 |
| **M4B-P3** | Output Quality & Sanitization | 測試 20 組常用 prompt；無 prompt leakage、無無效亂碼、無無窮迴圈重複 token；記錄 token diversity 與格式正確率 |
| **M4B-P4** | 推論速度與延遲（Pi 5） | 記錄 Time to First Token (TTFT) 與 Generation Speed (tokens/sec)；目標 TTFT ≤ 2.5s，Generation Speed ≥ 4.0 tok/sec (Pi 5) |
| **M4B-P5** | Timeout 處理 | 發送超長生成或極端 input 測試；達 timeout 門檻（如 15s）時觸發超時中斷，回傳錯誤代碼，不 hang 住 process |
| **M4B-P6** | Cooperative Cancel | 生成過程中送入 cancel 訊號（或 protocol cancel frame）；Child 在 500ms 內中斷生成並恢復 READY，不 crash |
| **M4B-P7** | Force Abort & Recovery Barrier | 模擬 Child unresponsive；執行 SIGTERM (Level 2) / SIGKILL (Level 3) + `waitpid()` proof，確認無 zombie/orphan；驗證重新 spawn child recovery barrier |
| **M4B-P8** | History Isolation | 連續執行 5 次單 turn 對話；驗證 Turn N 不受 Turn N-1 影響；無隱藏 KV cache 累積或 context pollution |
| **M4B-P9** | 同時常駐資源（M4a + M4b 模擬） | 與 M4a Audio (ASR/TTS) 共同常駐 Pi 5；Peak RSS ≤ 3.5GB (4GB target) 或 ≤ 6.0GB (8GB target)；記錄 CPU / Memory 使用曲線與 temperature peak（不得超過 80°C；獨立 soak 由 P10 覆蓋，本項為共同常駐快照） |
| **M4B-P10** | Thermal & Soak 穩定性 | 連續執行 20 次 session（間隔 5s）；CPU 溫度 < 80°C，無 thermal throttling 降頻，無 memory leak |
| **M4B-P11** | Build & Provenance | 從 clean Pi 5 依 script 可完成環境配置與執行；記錄 OS、Kernel、Python、Runtime、Model SHA-256；所有 dependencies 具開源 license |
| **M4B-P12** | Offline 驗證 | Pi 5 拔除網路線/關閉 Wi-Fi 下完整執行推論；log 證明無任何 external network call 或 API token 傳輸 |

---

## 6. 必要回交結構

POC repository 回交至少包含下列可定位內容；manifest 中的 relative path 必須完整：

```text
poc_llm/
├── deliveries/
│   └── DELIVERY-LLM-POC-M4B-VALIDATION-001.md
├── tools/
│   └── <reproducible M4b runner: child process + inference engine>
├── harness/
│   └── <prompt fixture + benchmark runner + validator>
└── evidence/m4b/
    ├── manifest.json
    ├── environment.txt
    ├── config.sanitized.*
    ├── results.*
    └── raw/
```

`manifest.json` 至少列：POC full SHA、hardware revision (Pi 5 8G/4G)、sanitized config SHA-256、runner 與 fixture SHA-256、candidate source hashes、model weights SHA-256、license、每個 M4B Test ID 狀態、raw artifact path、開始 / 結束時間與完整 reproduction command。未執行為 `Pending`，硬體或環境不足為 `Blocked`；不得標成 `Pass`。

---

## 7. Winner / No-Go 決定表（POC Gate 2 回交時逐項填寫）

| Decision item | Required answer |
| :--- | :--- |
| LLM Engine / Runtime | selected candidate、version、source SHA-256、license、理由與 rejected alternatives |
| Model candidate | model name、quantization method、file SHA-256、source URL / model card、license、Pi install command |
| Persistent child compliance | 是否完整通過 M4B-P1, P5, P6, P7, P8（含 protocol framing 與 waitpid proof） |
| 推論效能數據 | TTFT (P50 / P95)、Generation tok/sec、Peak RSS、Thermal peak (°C) |
| Format stability | JSON / intent 結構化輸出成功率（%） |
| Offline confirmation | 是否可在無網路 Pi 5 完整執行；log 是否無 credential / API endpoint |
| Residual risk | 已知限制、未通過項目、是否仍可達成 M4b contract；No-Go 條件說明 |

如任何 candidate 無法達成 M4B-P1 / P6 / P7 / P8 / P9 / P12 任一項，POC 須記錄可重現的 failure 並提出替代；不得宣告 Winner。

**效能門檻裁量說明**：M4B-P4 的效能目標（TTFT ≤ 2.5s、Generation Speed ≥ 4.0 tok/sec）為起始設計基準，非自動 No-Go 條件。若所有候選在 Pi 5 均未能達到目標值，POC 須記錄實際測量數字（P50 / P95）並回交，由 Core Designer 與 PM / User 協商門檻後再書面確認是否可接受；POC 不得在未取得 Core 書面確認前自行宣告效能可接受或選定 Winner。

---


## 8. 溝通順序（Contract relay flow）

```
Core Designer (contract owner)
  → [本 delivery] PM 正式轉交 LLM POC Team (relay owner)
    → POC Gate 0 回交 contract receipt + initial manifest
      → POC Gate 1 回交 candidate list & Ubuntu pre-screen evidence
        → Core Designer 書面確認 Gate 1 (存於 deliveries/)
          → POC Gate 2 執行 Pi 5 驗證，回交 exact 40-char source SHA + manifest
            → Core Designer 審核 → final winner ACK (或要求補交)
              → PM 通知 LLM POC Team ACK 結果
                → Developer 取得 Gate 2 final winner ACK → 建立 M4b 工作包
```

每個步驟的 ACK 均由 Core Designer 書面發出，存放於 `docs/outsource/deliveries/`；PM 只負責轉交，不代替 Core 簽發 ACK，也不代替 LLM POC Team 宣告 gate 通過。LLM POC Team 以自己 repo 完整 SHA 與 manifest 回交；不得以 branch HEAD 或部分 evidence 替代。

---

## 9. 本 contract 阻擋範圍摘要

| 阻擋項目 | 解除條件 |
| :--- | :--- |
| LLM POC 工作視為已正式授權 | Gate 0 POC Receipt + Gate 1 Core 書面確認 |
| Developer 加入 LLM production dependency lock | Gate 2 final winner ACK 後 |
| Developer 開始 LLM persistent child / adapter 實作 | Gate 2 final winner ACK 後（且 `docs/protocol.md` reviewed） |
| M4b 視為 Accepted | Gate 3：Core Tester 對 delivery exact SHA 驗收 PASS |
| M4c 啟動 | M4a + M4b 均取得 Tester 驗收 PASS（同一 delivery SHA） |
| M4 宣告 Accepted | M4a + M4b + M4c 同一 delivery SHA 全數 Tester PASS |
