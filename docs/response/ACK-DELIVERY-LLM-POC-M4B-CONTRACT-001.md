# Technical Response & ACK: DELIVERY-LLM-POC-M4B-CONTRACT-001

- **Response ID**: `ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Referenced Delivery ID**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Finding ID**: `OUT-M4B-2026-001`
- **Contract Owner**: Core Team Designer
- **Relay Owner**: PM
- **Responding Agent / Team**: LLM POC Team (Technical Lead & Developer)
- **Date**: 2026-08-15
- **Status**: `TEAM_ACK_ONLY — DOES NOT CLOSE EXTERNAL GATE`

> 本文件只記錄 POC Team 已閱讀合約，不是 Core Designer ACK，也不授權 Gate 1/2。
> External Gate 與 Internal Milestone 的目前狀態只以
> `docs/milestone/README.md` 為準。

---

## 1. 採用與邊界承接確認

LLM POC 團隊已完整檢視由 Core Designer 簽發、PM 轉交之 `DELIVERY-LLM-POC-M4B-CONTRACT-001` 合約，並確認承接以下所有責任邊界與約束：

1. **職責範圍**：POC 團隊負責技術探索、候選模型/Runtime 評估、Persistent Child Process 參考封裝、Raspberry Pi 5 驗證與可重現 Evidence 交付；Core Team 保留 Model Baseline 最終定案、Protocol 契約審核與最終 ACK 決定權。
2. **授權約束**：在各 Gate 取得 Core Designer 書面 ACK 前，所有 POC 提案維持 `Proposed` 狀態，不直接修改主線依賴或將 POC 程式碼視為產品主線實作。
3. **安全與衛生規範**：嚴格遵守 Model 權重檔、大型 Raw Results、Private Prompts/Transcripts 與連線帳密不入 Git 政策。

---

## 2. 外部 Gate 生命週期與內部執行映射

POC 團隊已將內部工作規劃與合約之 4 大 Gate 進行精確對齊：

| Gate | 合約階段定義 | POC 團隊對應行動與內部映射 |
| :--- | :--- | :--- |
| **Gate 0** | Contract Receipt & Scope Confirmation | • 建立本內部 team ACK<br>• 於 `docs/delivery/` 產出對外 receipt，並於 `poc_llm/deliveries/` 提交實際 Initial Manifest<br>• PM 記錄實際 HEAD、Core Designer 登錄後才完成 Gate 0；本 ACK 不授權 Gate 1/2 |
| **Gate 1** | Candidate Proposal & Ubuntu Pre-screening | • 整理 Gemma-2-2B, Qwen2.5-1.5B/3B, SmolLM2-1.7B 與 LiteRT-LM / llama.cpp 清單<br>• 提供 Exact Version, Source SHA-256, License Table<br>• 提交 Ubuntu x86/arm64 初篩數據，等待 Core Designer 5 日內書面確認 |
| **Gate 2** | Pi 5 驗證 / Benchmark / Persistent-Child 契約 | • 於 Pi 5 執行 M4B-P1 ~ M4B-P12 全套不可變測試<br>• 回交 Exact 40-char SHA、Sanitized Evidence、Validation 報告與 Winner/No-Go 決定表<br>• 取得 Core Designer Final Winner ACK |
| **Gate 3** | Core Production Implementation | • 配合主線團隊進行 M4b 產品化 Handoff（`model_spec.md` 與 `protocol.md`） |

---

## 3. 測試驗收項目 (M4B-P1 ~ M4B-P12) 承接矩陣

內部 Harness 與測試封包將直接以合約之 12 項要求作為驗收基準：

| ID | 測試項目 | 承接門檻與實作策略 | 內部狀態 |
| :--- | :--- | :--- | :---: |
| **M4B-P1** | Persistent Child Lifecycle | 啟動與 READY Handshake $\le$ 10s；stdin/stdout JSON-lines framing；無殘留行程 | `PLANNED` |
| **M4B-P2** | Single-turn Inference & Result | 結構化 JSON Intent (`speak`/`tool`/`rest`) 穩定輸出；模型不執行 Tool | `PLANNED` |
| **M4B-P3** | Output Quality & Sanitization | 20 組常用 Prompt 測試；無 Prompt leakage、無無效亂碼、無無窮迴圈 | `PLANNED` |
| **M4B-P4** | 推論速度與延遲 (Pi 5) | 起始基準：TTFT $\le$ 2.5s，生成速度 $\ge$ 4.0 tok/sec（依實測協商） | `PLANNED` |
| **M4B-P5** | Timeout 處理 | 15s 逾時門檻中斷機制，回傳標準錯誤，不 Hang 行程 | `PLANNED` |
| **M4B-P6** | Cooperative Cancel | 500ms 內中斷生成並恢復 READY，無 Crash | `PLANNED` |
| **M4B-P7** | Force Abort & Recovery Barrier | SIGTERM (L2) $\to$ SIGKILL (L3) 升級，附 `waitpid()` 證明 `orphan=0`，驗證 Rebuild 重建 | `PLANNED` |
| **M4B-P8** | History Isolation | 連續 5 次單 Turn 對話，驗證 Turn $N$ 不受 Turn $N-1$ 影響，無隱藏 KV state 累積 | `PLANNED` |
| **M4B-P9** | 同時常駐資源 (M4a+M4b) | 與 M4a Audio 共同常駐：Peak RSS $\le$ 3.5GB (4GB) / $\le$ 6.0GB (8GB)；溫度 $< 80^\circ\text{C}$ | `PLANNED` |
| **M4B-P10** | Thermal & Soak 穩定性 | 連續 20 次 Session（間隔 5s）；無 Thermal Throttling，無 Memory Leak | `PLANNED` |
| **M4B-P11** | Build & Provenance | Clean Pi 5 配置 Script，記錄完整 SHA-256，所有依賴具開源 License | `PLANNED` |
| **M4B-P12** | Offline 驗證 | 完全拔除網路執行，Log 證明無任何外部連線或 API Token 傳輸 | `PLANNED` |

---

## 4. 結論與下一步

本 ACK 只確認 LLM POC 團隊理解並承接合約規範。修訂後外部 receipt 以
`DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md` 提交 PM；Gate 0 是否完成由 PM/Core
依實際收件與登錄決定。
