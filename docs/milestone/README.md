# LLM POC Milestone Index

本檔是目前 LLM POC milestone 狀態的唯一入口。依據 Core Designer 正式合約 `DELIVERY-LLM-POC-M4B-CONTRACT-001`，全案分為 Gate 0（簽收與 Initial Manifest）、Gate 1（候選初篩）與 Gate 2（Pi 5 完整驗證）。

## Current Status

最後更新：2026-08-15

最終交付可達性：`IN_ALIGNMENT` — 已收到正式 M4b 合約 `DELIVERY-LLM-POC-M4B-CONTRACT-001`，已完成內部技術審查 `ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001.md`，並已建立 `DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md`。

| Milestone / Gate | 狀態 | 摘要 | 依據/文件 |
| --- | --- | --- | --- |
| **Gate 0 / M0** | `IN_PROGRESS` | 合約接收、範圍確認、Initial Manifest 與 Pi/Environment Readiness | [M0](m0_llm_readiness.md) / [Gate 0 Receipt](../delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md) |
| **Gate 1 / M1** | `PLANNED` | 候選提案（Gemma-2-2B, Qwen2.5-1.5B/3B, SmolLM2-1.7B, LiteRT-LM, llama.cpp）與 Ubuntu 初篩 | [M1](m1_llm_contract_and_harness.md) / [M2](m2_llm_candidate_evaluation.md) |
| **Gate 2 / M2-M4** | `PLANNED` | 在 Pi 5 上執行 M4B-P1 至 M4B-P12 全套驗證、Persistent Child、散熱/資源與 Winner 決定 | [M3](m3_llm_child_pi_integration.md) / [M4](m4_llm_combined_validation_and_delivery.md) |

## Delivery Mapping (對齊 M4b 合約 12 項驗證清單)

| 驗證類別 | 對應項目 | 主要驗收條件 |
| --- | --- | --- |
| D1 Governance & Protocol | M4B-P1, M4B-P2, M4B-P8 | Persistent Child READY $\le$ 10s、JSON Intent 輸出、單 Turn 隔離 |
| D2 Output Quality & Sanitization | M4B-P3 | 20 組 Prompt 無 Leakage、無亂碼、無無窮迴圈 |
| D3 Performance & Latency | M4B-P4 | TTFT $\le$ 2.5s、生成速度 $\ge$ 4.0 tok/sec 基準 |
| D4 Cancel & Recovery | M4B-P5, M4B-P6, M4B-P7 | Timeout 15s、Cancel $\le$ 500ms、Force Abort + `waitpid()` 證明 `orphan=0` |
| D5 Resource & Thermal | M4B-P9, M4B-P10 | M4a 共存 Peak RSS $\le$ 3.5G/6.0G、CPU 溫度 $< 80^\circ\text{C}$、20 次 Soak |
| D6 Provenance & Offline | M4B-P11, M4B-P12 | Clean 配置腳本、Exact SHA-256、開源 License、無網路完全離線驗證 |

## Open Dependencies and Risks

- Gate 0 Receipt 待 User 最終 Review 與 Commit SHA 標記後交付 PM。
- Gate 1 候選清單提交後需由 Core Designer 在 5 個工作日內發出書面確認。
- Accepted M4a Audio HAL full SHA、owner 與取得路徑待 Audio 團隊提供登錄。

## Governing Documents

- [LLM POC 合約 (Income)](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [LLM POC 內部技術 ACK (Response)](../response/ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Gate 0 簽收回條 (Delivery)](../delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md)
- [LLM POC 工作流程與合作方式](../llm_poc_workflow.md)
- [文件總索引](../DOCUMENT_INDEX.md)
- [POC workspace/Pi 使用入口](../../poc_llm/README.md)

