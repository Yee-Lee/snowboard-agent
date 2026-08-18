# LLM POC Milestone and Contract Gate Index

本檔是 LLM POC 外部 Contract Gate、內部 execution milestone、目前授權範圍與
風險的唯一狀態入口。External Gate 由合約 owner/recorder 關閉；Internal Milestone
由 POC workflow 的 entry/exit review 控制，兩者不得共用狀態。

最後更新：2026-08-18

## Current Delivery Reachability

最終交付可達性：`GATE0_R2_COMPLETE_M0_GATE_REVIEW`。

Core Designer 已複驗 `llm` / `0d415d174390665ed92793937d30334f01e3df14`，
關閉 `OUT-M4B-2026-007-A～D`，並正式登錄 Gate 0 R2 `COMPLETE`。PM handoff 015
已解決；此 ACK 僅接受 planning/regression packet，不代表已執行 Ubuntu benchmark、
Pi run 或 candidate evidence。

## External Contract Gates

| Gate | 狀態 | Owner / recorder or approver | 關閉條件 | 下一個允許動作 |
| --- | --- | --- | --- | --- |
| **Gate 0** Contract Receipt | `COMPLETE` | POC Team 提交；PM 收件；Core Designer 已登錄 | `0d415d...` 複驗通過；OUT-M4B-2026-007-A～D 已關閉 | 進行 M0 entry review；不自動啟動 M0 |
| **Gate 1** Candidate Proposal & Ubuntu Pre-screen | `NOT_STARTED / BLOCKED` | POC Team 提交；Core Designer 書面確認 | 固定 pairing、license/offline/provenance preflight、Ubuntu x86/arm64 初篩及最多兩個 finalists 均完整 | Core Designer ACK 後才可進 Gate 2A |
| **Gate 2A** Pi 5 LLM-only | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核 | P1～P8、P10A、P11、P12 依 matrix 完成 | 只能產生 provisional finalist ACK |
| **Gate 2B** Audio+LLM combined | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核 | Accepted Audio package、P9、P10B 及固定 2A regression 全部通過 | Core Designer 才可發 final winner ACK |
| **Gate 3** Core Production | `OUT_OF_POC_SCOPE` | Core Developer / Tester / Designer | 依 Core contract | POC 僅提供 accepted handoff material |

POC Team 的 ACK、self-test 或 Technical Lead review 都不能把 External Gate 標成
`COMPLETE`；只有上表指定的 recorder/approver 可以關閉對應 Gate。

## Internal Execution Milestones

| Milestone | 狀態 | 摘要 | 依據 |
| --- | --- | --- | --- |
| **M0** | `GATE_REVIEW` | `M0-RUN-001` 執行完成；Technical Lead `PASS recommendation`，待 Internal Tester confirmation | [M0](m0_llm_readiness.md) |
| **M1** | `PLANNED` | Freeze boundary/harness，固定 candidate pairing 與 preflight | [M1](m1_llm_contract_and_harness.md) |
| **M2** | `PLANNED` | Ubuntu x86/arm64 pre-screen，最多保留兩個 Pi finalists | [M2](m2_llm_candidate_evaluation.md) |
| **M3** | `PLANNED` | Gate 2A：Pi 5 LLM-only P1～P8、P10A、P11、P12；provisional finalist | [M3](m3_llm_child_pi_integration.md) |
| **M4** | `PLANNED` | Gate 2B：Accepted Audio package、P9、P10B、2A regression；final winner | [M4](m4_llm_combined_validation_and_delivery.md) |

Internal M0 已完成 entry、packet execution 與 Technical Lead evidence review；只有
Internal Tester confirmation 通過後才可標示 `COMPLETE`。M0 完成也不能取代
Gate 1 Core Designer ACK。

## Delivery Taxonomy and Traceability

唯一 delivery taxonomy 為 D1–D8。External Gate、Internal Milestone、Delivery Area、
M4B-P1～P12、owner、delivery item 與 evidence 狀態的唯一 crosswalk 見
[M4b Traceability Crosswalk](m4b_traceability_crosswalk.md)。其他文件只能引用該表，
不得另建競爭映射。

## Open Dependencies, Risks and Adjustment Requests

- **Gate review — Internal M0**：`afb310b...` 上的 inventory、exact-SHA/clean
  proof、marker checksum/cleanup 與 lifecycle 皆支持 Technical Lead `PASS recommendation`。
  下一個唯一獲准工作是 Internal Tester 獨立 confirmation；在此之前不啟動 M1。
- **Forward risk — Gate 2A swap**：M0 盤點發現 4GB Pi 配置約 2GB swap（未使用）。
  Gate 2A 的 mandatory environment 仍要求 `swap=0`；屆時需獨立授權，不在 M0 修改。
- **Dependency — Gate 1 candidate proposal**：研究參考建議以 LiteRT-LM v0.16.0
  配對 Gemma4-E2B、Qwen2.5-1.5B 與 Qwen2.5-0.5B；尚未完成 exact artifact、
  license、offline 與 provenance manifest，也未凍結 candidate。
- **Risk — Ubuntu arm64 availability**：Gate 1 所需 Ubuntu arm64 runner 尚未登錄；若無
  native runner，必須提出可重現替代方案並取得 Core Designer 同意，不能以 x86 結果代替。
- **Dependency — M4a**：Accepted M4a Audio HAL full SHA、owner 與取得路徑仍待提供。
- **Adjustment request**：無門檻降低請求；若硬體/runner 不可用，應記為 `Blocked` 或
  `INCONCLUSIVE`，不得改寫為通過。

## Gate 0 R2 Submission Package

- [Core Final ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md)
- [Readiness correction response](../response/RESP-POC-LLM-READINESS-2026-001.md)
- [015 response](../response/RESP-PM-OUT-260817-015.md)
- [Revised Gate 0 receipt](../delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md)
- [Gate 0 initial manifest R2](../../poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md)
- [M4b traceability crosswalk](m4b_traceability_crosswalk.md)
- [Authoritative execution plan](m4b_execution_plan.md)
- [OUT-M4B-2026-007-A～D response](../response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md)
- [Gate 1 packet](../../poc_llm/tests/gate1/GATE1-PACKET-003.md)
- [M0 test request](../../poc_llm/tests/m0/M0-TEST-REQUEST-001.md)

## Governing Documents

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Gate 0 R2 Final ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md)
- [LiteRT-LM candidate research reference](../pm_handoff/PM-POC-LLM-20260818-002-litert-lm-candidate-research-reference.md)
- [PM-OUT-260817-015 (resolved history)](../pm_handoff/history/PM-OUT-260817-015-llm-poc-contract-plan-review.md)
- [Gate 0 R2 revision request (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md)
- [Gate 0 R2 Revision 002 (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md)
- [Readiness correction (history)](../pm_handoff/history/PM-POC-LLM-20260817-001-readiness-correction.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [POC workspace/Pi entry point](../../poc_llm/README.md)
