# LLM POC Team → PM → Core Team: M4b LLM POC Gate 0 Receipt & Initial Manifest

- **Delivery ID**: `DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT`
- **In Response To**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Finding ID**: `OUT-M4B-2026-001`
- **From**: LLM POC Team
- **To**: PM (轉交 Core Team Designer)
- **Date**: 2026-08-15
- **Status**: `GATE 0 COMPLETE — READY FOR GATE 1 CANDIDATE PROPOSAL`
- **POC Intake Commit SHA**: `PENDING_OPERATOR_COMMIT`

---

## 1. 簽收聲明與邊界確認 (Contract Receipt & Scope Confirmation)

LLM POC 團隊已於 2026-08-15 正式接收並完整審閱由 Core Team Designer 制定、經 PM 轉交之 `DELIVERY-LLM-POC-M4B-CONTRACT-001` 合約。

我們在此確認：
1. **完全採納合約邊界**：POC 團隊負責候選推論引擎探索、Persistent Child Process 參考封裝、Raspberry Pi 5 驗證與可重現 Evidence 交付；Core Team 保留 Model Baseline 定案、Protocol 審核與最終 ACK 決定權。
2. **遵守 4 大 Gate 生命週期**：未取得各 Gate 的 Core Designer 書面 ACK 前，所有 POC 項目維持 `Proposed`，不提早將 POC 封裝直接作為主線依賴。
3. **承接 M4B-P1 至 M4B-P12 驗證清單**：全套 12 項測試指標（包含 Persistent Child 生命週期 $\le$ 10s、JSON Intent 輸出、TTFT $\le$ 2.5s / 速度 $\ge$ 4.0 tok/sec 基準、Cancel $\le$ 500ms、Force Abort + `waitpid()` 證明、Single-turn 歷史隔離、M4a 共存 Peak RSS $\le$ 3.5GB/6.0GB、溫度 $< 80^\circ\text{C}$、20 次 Soak、Clean Script 與完全離線運作）作為後續 Gate 2 驗收唯一依據。

---

## 2. 初始工作區結構與 Initial Manifest (Workspace Layout)

POC 團隊已於本儲存庫中建立標準隔離工作區 `poc_llm/`，其結構如下：

```text
poc_llm/
├── deliveries/               # POC 交付文件與 Validation 報告
├── evidence/                 # Sanitized evidence 索引與測試結果摘要
│   └── m4b/
│       ├── manifest.json     # 測試執行清單、SHA-256、License 與狀態
│       ├── environment.txt   # Pi 5 / Ubuntu 硬體與 OS 規格記錄
│       └── results/          # 結構化測試結果 (JSON/Markdown)
├── fixtures/                 # 非敏感測試 Prompt、Schema 與 Catalog
├── src/                      # Reference Runtime、Child Process Protocol & Client
├── tests/                    # Deterministic Fake Harness、Protocol & Unit Tests
├── tools/                    # 可重現 Setup、Benchmark Runner & Evidence Collector
└── README.md                 # 工作區指引與受控執行政策
```

---

## 3. Gate 1 候選初篩計畫摘要 (Candidate Pre-screening Plan)

依合約 §3 規定，POC 團隊於 Gate 1 提出的候選提案將包含：

* **推論引擎 (Engines)**：
  1. `LiteRT-LM` (Google TFLite / MediaPipe LLM)
  2. `llama.cpp` (GGUF 推論引擎，作為對照與備選)
* **模型候選 (Models, $\le$ 3B)**：
  1. `Gemma-2-2B-IT` (Google)
  2. `Qwen2.5-1.5B-Instruct` / `Qwen2.5-3B-Instruct` (Alibaba)
  3. `SmolLM2-1.7B-Instruct` (HuggingFace)
* **量化格式 (Quantization)**：
  - INT4、INT8、GGUF (Q4_K_M / Q8_0)
* **提示詞與格式 (Prompt & Format)**：
  - 繁體中文 (zh-TW) / 英文 System Prompt，要求嚴格輸出結構化 JSON Intent (`speak` / `tool` / `rest`)。

---

## 4. 資料安全與衛生保證 (Data & Artifact Hygiene Assurance)

POC 團隊嚴格落實以下安全原則：
- 任何模型權重檔（.bin / .gguf / .tflite / .task 等）、大型 Raw Results、Private Prompts / Transcripts 及 SSH 連線金鑰**絕不進入 Git 儲存庫**。
- Git 僅記錄可公開之開源來源 URL、檔案 SHA-256 Checksum、License 授權類別、非敏感 Fixtures 與 Sanitized Evidence Summaries。

---

## 5. Gate 0 結案與 Gate 1 啟動請求

1. **Gate 0 狀態**：`COMPLETE`（已完成合約接收、範圍確認、工作區配置與 Initial Manifest 定義）。
2. **請求動作**：請 PM 轉交本回條予 Core Team Designer 備查，並授權 LLM POC 團隊正式啟動 **Gate 1（候選提案與 Ubuntu 初篩測試）**。
