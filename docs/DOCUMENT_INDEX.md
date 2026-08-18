# Document Index (Income, Response, Delivery & Working Plan)

這份文件用於追蹤我們從外部團隊（PM / Core Team）收到的文件 (Income)、歷史已完成訊息 (Income History)、內部技術確認 (Response)、我們要交付給外部團隊的文件 (Delivery)，以及內部執行計畫 (Working Plan)。

## 1. Income (位於 `docs/pm_handoff/`)
這些文件是從外部接收的任務、合約與需求，對本團隊為**嚴格唯讀 (Read-only)**：

* [`DELIVERY-LLM-POC-M4B-CONTRACT-001.md`](pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md) - Core Designer M4b contract，2026-08-17 revision，包含 OUT-M4B-2026-002～006
* [`PM-OUT-260817-015-llm-poc-contract-plan-review.md`](pm_handoff/PM-OUT-260817-015-llm-poc-contract-plan-review.md) - Core contract / plan review 原始 brief
* [`core_llm_m4b_tasks.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/pm_handoff/core_llm_m4b_tasks.md) - M4b LLM 任務需求與邊界規範
* [`PM-POC-LLM-20260817-001-readiness-correction.md`](pm_handoff/PM-POC-LLM-20260817-001-readiness-correction.md) - Gate 0/M0、Ubuntu pre-screen、traceability、executable packet 與 authority boundary 修正；`On hold — pending PM-OUT-260817-015`

## 2. Income History (位於 `docs/pm_handoff/history/`)
已完成處理、被新合約取代或不再處於活動狀態的 handoff 訊息，歸檔於此，**代表已完成不必重複追蹤**：

* `DELIVERY-AUDIO-POC-M3-ACK-001.md` - (歷史) Audio M3 HAL 合約採用確認
* `core_audio_m3_requirements.md` - (歷史) 舊主線 M3 音訊要求
* `audio_poc_delivery_checklist.md` - (歷史) 舊 Audio 交付清單
* `audio_poc_development_guide.md` - (歷史) 舊 Audio 開發指引

## 3. Response (位於 `docs/response/`)
POC 團隊內部的技術確認、評估結果或對外部 Income 的技術 ACK：

* [`ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/response/ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001.md) - M4b 合約內部技術審查與 12 項測試指標承接確認
* [`RESP-POC-LLM-READINESS-2026-001.md`](response/RESP-POC-LLM-READINESS-2026-001.md) - 逐 finding 修訂回覆；Team revised 不代表 PM/Core 已關閉 finding
* [`RESP-PM-OUT-260817-015.md`](response/RESP-PM-OUT-260817-015.md) - 015 複驗回覆、changed paths 與 remaining Core decisions
* [`ACK-DELIVERY-AUDIO-POC-M3-001.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/response/ACK-DELIVERY-AUDIO-POC-M3-001.md) - (歷史) Audio M3 HAL 採用存檔確認

## 4. Delivery (位於 `docs/delivery/`)
我們要對外正式交付給外部團隊（由 PM 轉交）的文件，命名規範為 `DELIVERY-{流水號}-{to_who}-{title}.md`：

* [`DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md) - 回覆 `DELIVERY-LLM-POC-M4B-CONTRACT-001` 的 Gate 0 簽收回條與 Initial Manifest
* [`POC-llm-DEL-2026-001-R1.md`](../poc_llm/deliveries/POC-llm-DEL-2026-001-R1.md) - 實際 Gate 0 Initial Manifest；未執行項目明列 Pending/Blocked
* [`POC-llm-DEL-2026-001-R2.md`](../poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md) - 015 修訂後 Gate 0 Initial Manifest；R1 已 superseded

## 5. Working Plan (位於 `docs/milestone/`)
Repo-owned 內部執行工作文件：

* [`README.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/README.md) - LLM POC milestone 單一狀態入口
* [`llm_delivery_gate_draft.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/llm_delivery_gate_draft.md) - 交付映射草案
* [`m4b_traceability_crosswalk.md`](milestone/m4b_traceability_crosswalk.md) - External Gate、Internal Milestone、D1–D8、M4B-P1～P12 與 evidence owner 的唯一 crosswalk
* [`m4b_execution_plan.md`](milestone/m4b_execution_plan.md) - Gate 1、Gate 2A、Gate 2B authoritative work-package plan
* [`m0_llm_readiness.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/m0_llm_readiness.md) - LLM environment/evidence-chain readiness
* [`m1_llm_contract_and_harness.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/m1_llm_contract_and_harness.md) - 契約、門檻與 deterministic harness
* [`m2_llm_candidate_evaluation.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/m2_llm_candidate_evaluation.md) - runtime/model 候選初篩與比較
* [`m3_llm_child_pi_integration.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/m3_llm_child_pi_integration.md) - persistent child 與 Pi 整合
* [`m4_llm_combined_validation_and_delivery.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/milestone/m4_llm_combined_validation_and_delivery.md) - combined validation 與最終交付
