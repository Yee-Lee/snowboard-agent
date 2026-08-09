# LLM POC Milestone Index

本檔是目前 LLM POC milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4
是正式 POC delivery milestones。舊 Audio POC milestone 文件只保留為歷史參考，
不得用來判定本計畫狀態。

## Current Status

最後更新：2026-08-09

最終交付可達性：`AT_RISK` — LLM POC 計畫已重建，但 M0 尚未開始；正式
LLM delivery checklist、development guide、Designer-frozen gates 與 accepted M4a
Audio HAL SHA 仍未取得。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `NOT_STARTED` | LLM Pi/environment 與 evidence-chain readiness；尚未執行或判定 | [M0](m0_llm_readiness.md) |
| M1 | `NOT_STARTED` | 凍結 Reasoner/prompt/output/child protocol、資源 gate，建立 deterministic harness | [M1](m1_llm_contract_and_harness.md) |
| M2 | `NOT_STARTED` | 在固定 gate 下比較 LiteRT-LM runtime/model/quantization candidates | [M2](m2_llm_candidate_evaluation.md) |
| M3 | `NOT_STARTED` | 固定 winner/no-go，驗證 persistent child、cancel/cleanup 與 Pi 5 整合 | [M3](m3_llm_child_pi_integration.md) |
| M4 | `NOT_STARTED` | 接受的 M4a SHA 上完成至少 20 個 combined sessions、offline/failure injection 與交付 | [M4](m4_llm_combined_validation_and_delivery.md) |

目前只完成計畫與工作方法修正。這項文件工作不構成 M0 entry，也不產生任何
hardware `PASS`。

## Next Planned Milestone — M0 Has Not Started

下一個 milestone 是 M0，但必須在以下 entry review 完成後，才可將 M0 改為
`IN_PROGRESS`：

1. User 明確核准開始 M0 與唯讀 Pi 操作。
2. M0 test packet、evidence schema、允許的命令與 cleanup 方法已完成 review。
3. 要測試的完整 commit SHA 可供 Pi checkout，且 workstation/Pi worktree 都可驗證 clean。
4. SSH endpoint、credential、model/artifact 位置只保存在 operator-managed 設定，不進 Git。
5. M0 不下載模型、不安裝 runtime、不執行正式 benchmark，也不沿用 Audio M0 的
   `PASS` 作為 LLM M0 結果。

## Delivery Mapping

目前依 [LLM Delivery Gate Working Draft](llm_delivery_gate_draft.md) 追蹤工作。
該文件是 repo-owned working plan，不取代尚未收到的 PM/Designer 正式 checklist。

| Delivery area | Primary milestone |
| --- | --- |
| D1 Governance、manifest、exact SHA 與 evidence index | M0–M4 |
| D2 Reproducible runtime、model、artifact、license 與 strict config | M1–M3 |
| D3 Prompt/output boundary、child protocol、cancel 與 cleanup | M1–M3 |
| D4 合法 action、fallback、capability 與 history isolation | M1–M3 |
| D5 Pi 5 latency、throughput、RSS、CPU、disk 與 thermal | M2–M3 |
| D6 Accepted M4a SHA、20 sessions、offline 與 failure injection | M4 |
| D7 唯一 winner 或 evidence-backed no-go | M2–M4 |
| D8 Data/log/artifact safety 與 internal-review handoff | M0–M4 |

## Open Dependencies and Risks

- `docs/pm_handoff/llm_poc_delivery_checklist.md` 尚未由 PM/Designer 交付。
- `docs/pm_handoff/llm_poc_development_guide.md` 尚未由 PM/Designer 交付。
- Reasoner 的 PromptBuilder、`LLMResponse`、normalizer、validator、P5 fallback 與
  capability view 尚未由 Designer 凍結。
- Runtime/model/quantization、context/output limits、threads、timeout 與資源門檻尚未凍結。
- Accepted M4a Audio HAL full SHA、owner、Test ID 與取得路徑尚未登錄。
- 目前本地分支 SHA 必須依 commit/push 核准流程進入可被 Pi fetch 的 exact-SHA 流程。

上述風險不阻止計畫文件維護，但會阻止對應 milestone 的 gate closure。

## Status and Result Rules

Milestone 狀態流轉、必要的同步更新與硬體結果判定，統一遵循
[LLM POC workflow](../llm_poc_workflow.md)；本索引只記錄目前狀態與風險。

## Governing Documents

- [LLM POC 工作流程與合作方式](../llm_poc_workflow.md)
- [LLM Delivery Gate Working Draft](llm_delivery_gate_draft.md)
- [核心團隊 M4b LLM 任務（Income；目前仍待 PM 正式交付）](../pm_handoff/core_llm_m4b_tasks.md)
- [文件索引](../DOCUMENT_INDEX.md)
- [POC workspace/Pi 使用入口](../../poc_llm/README.md)

正式 LLM delivery checklist 與 development guide 收到後，必須先做差異分析；若
它們改變 gate、scope 或 evidence semantics，更新本索引並提出 change request，
不得靜默覆蓋既有結果。

## Historical Audio Material

下列舊文件只保留為 Audio POC 歷史證據，不是目前活動計畫：

- [M0 remote environment](../archive/audio_poc/milestone/m0_remote_environment.md)
- [M1 frozen-gate draft](../archive/audio_poc/milestone/m1_frozen_gates_draft.md)
- [M1 test/audio baseline](../archive/audio_poc/milestone/m1_test_and_audio_baseline.md)
- [M2 candidate evaluation](../archive/audio_poc/milestone/m2_candidate_evaluation.md)
- [M3 hardware integration](../archive/audio_poc/milestone/m3_real_hardware_integration.md)
- [M4 combined validation](../archive/audio_poc/milestone/m4_combined_validation_and_delivery.md)
