# Document Index (Income & Outcome)

這份文件用於追蹤我們從外部團隊（如 PM 或設計）收到的文件 (Income) 以及我們要交付給外部團隊的文件 (Outcome)。

## Income (位於 `docs/pm_handoff/`)
這些文件是從外部接收的任務、需求與檢查清單，對於開發團隊而言是**唯讀 (Read-only)** 的：

* `core_llm_m4b_tasks.md` - M4b LLM 任務需求與邊界規範
* `llm_poc_delivery_checklist.md` - (待建立) LLM M4b 最終交付查檢表
* `llm_poc_development_guide.md` - (待建立) LLM Child Process 開發指南

*(註：原 Audio 團隊的交接文件如 `audio_poc_delivery_checklist.md` 等亦保留於此作為歷史參考)*

## Working Plan (位於 `docs/milestone/`)

以下是 repo-owned 工作文件，不冒充尚未交付的 PM/Designer Income：

* `README.md` - LLM POC milestone 單一狀態入口
* `llm_delivery_gate_draft.md` - 正式 checklist 交付前使用的 delivery mapping；狀態為 `NOT_FROZEN`
* `m0_llm_readiness.md` - LLM environment/evidence-chain readiness
* `m1_llm_contract_and_harness.md` - frozen contract、gates 與 deterministic harness
* `m2_llm_candidate_evaluation.md` - runtime/model/quantization 候選比較
* `m3_llm_child_pi_integration.md` - persistent child 與 Pi integration baseline
* `m4_llm_combined_validation_and_delivery.md` - accepted M4a combined validation 與交付

舊 Audio milestone 文件保留在 `docs/archive/audio_poc/milestone/` 作歷史參考；
其狀態不適用於目前 LLM POC，且不會被活動 milestone 掃描讀取。

## Outcome (位於 `docs/delivery/`)
這些文件是我們要對外正式交付的紀錄，命名規範為 `DELIVERY-{流水號}-{to_who}-{title}.md`：

* (目前尚未有交付紀錄，未來將於此處新增)
