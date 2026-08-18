# LLM POC Milestone and Contract Gate Index

本檔是 LLM POC 外部 Contract Gate、內部 execution milestone、目前授權範圍與
風險的唯一狀態入口。External Gate 由合約 owner/recorder 關閉；Internal Milestone
由 POC workflow 的 entry/exit review 控制，兩者不得共用狀態。

最後更新：2026-08-18

## Current Delivery Reachability

最終交付可達性：`GATE0_R2_SUBMITTED_PENDING_CORE_INTAKE`。

POC Team 已收到 2026-08-17 Core contract revision 與 015 對 `0cff62f...` 的退件，並
完成 R2 committed planning packet。`SUBMITTED` 在本修訂 commit push 後生效；Core
Designer 對 exact SHA intake 前不得標示 `COMPLETE`。本輪沒有 Ubuntu benchmark、Pi
run 或 candidate evidence；目前只授權 scaffold 與 harness self-test。

## External Contract Gates

| Gate | 狀態 | Owner / recorder or approver | 關閉條件 | 下一個允許動作 |
| --- | --- | --- | --- | --- |
| **Gate 0** Contract Receipt | `SUBMITTED R2 / PENDING CORE INTAKE` | POC Team 提交；PM 收件；Core Designer 登錄 | Core 對 R2 exact SHA 確認 revision receipt、Initial Manifest、Gate 1 packet 與 2A/2B plan | 等待複驗；不執行 benchmark |
| **Gate 1** Candidate Proposal & Ubuntu Pre-screen | `NOT_STARTED / BLOCKED` | POC Team 提交；Core Designer 書面確認 | 固定 pairing、license/offline/provenance preflight、Ubuntu x86/arm64 初篩及最多兩個 finalists 均完整 | Core Designer ACK 後才可進 Gate 2A |
| **Gate 2A** Pi 5 LLM-only | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核 | P1～P8、P10A、P11、P12 依 matrix 完成 | 只能產生 provisional finalist ACK |
| **Gate 2B** Audio+LLM combined | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核 | Accepted Audio package、P9、P10B 及固定 2A regression 全部通過 | Core Designer 才可發 final winner ACK |
| **Gate 3** Core Production | `OUT_OF_POC_SCOPE` | Core Developer / Tester / Designer | 依 Core contract | POC 僅提供 accepted handoff material |

POC Team 的 ACK、self-test 或 Technical Lead review 都不能把 External Gate 標成
`COMPLETE`；只有上表指定的 recorder/approver 可以關閉對應 Gate。

## Internal Execution Milestones

| Milestone | 狀態 | 摘要 | 依據 |
| --- | --- | --- | --- |
| **M0** | `NOT_STARTED` | Environment、exact SHA、command lifecycle 與 evidence-chain readiness | [M0](m0_llm_readiness.md) |
| **M1** | `PLANNED` | Freeze boundary/harness，固定 candidate pairing 與 preflight | [M1](m1_llm_contract_and_harness.md) |
| **M2** | `PLANNED` | Ubuntu x86/arm64 pre-screen，最多保留兩個 Pi finalists | [M2](m2_llm_candidate_evaluation.md) |
| **M3** | `PLANNED` | Gate 2A：Pi 5 LLM-only P1～P8、P10A、P11、P12；provisional finalist | [M3](m3_llm_child_pi_integration.md) |
| **M4** | `PLANNED` | Gate 2B：Accepted Audio package、P9、P10B、2A regression；final winner | [M4](m4_llm_combined_validation_and_delivery.md) |

Internal M0 在 entry review、test request 核准及 Pi 操作授權前保持 `NOT_STARTED`。
Gate 0 行政收件完成不會自動啟動 M0，M0 完成也不能取代 Gate 1 Core Designer ACK。

## Delivery Taxonomy and Traceability

唯一 delivery taxonomy 為 D1–D8。External Gate、Internal Milestone、Delivery Area、
M4B-P1～P12、owner、delivery item 與 evidence 狀態的唯一 crosswalk 見
[M4b Traceability Crosswalk](m4b_traceability_crosswalk.md)。其他文件只能引用該表，
不得另建競爭映射。

## Open Dependencies, Risks and Adjustment Requests

- **Blocker — Gate 0 R2 intake**：015 已收件；Core Designer 尚未對 R2 exact SHA 複驗。
- **Blocker — Internal M0 authorization**：Pi 5 4GB/8GB availability、operator access 與
  immutable test request 尚待 entry review；M0 仍為 `NOT_STARTED`。
- **Risk — Ubuntu arm64 availability**：Gate 1 所需 Ubuntu arm64 runner 尚未登錄；若無
  native runner，必須提出可重現替代方案並取得 Core Designer 同意，不能以 x86 結果代替。
- **Dependency — M4a**：Accepted M4a Audio HAL full SHA、owner 與取得路徑仍待提供。
- **Adjustment request**：無門檻降低請求；若硬體/runner 不可用，應記為 `Blocked` 或
  `INCONCLUSIVE`，不得改寫為通過。

## Gate 0 R2 Submission Package

- [Readiness correction response](../response/RESP-POC-LLM-READINESS-2026-001.md)
- [015 response](../response/RESP-PM-OUT-260817-015.md)
- [Revised Gate 0 receipt](../delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md)
- [Gate 0 initial manifest R2](../../poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md)
- [M4b traceability crosswalk](m4b_traceability_crosswalk.md)
- [Authoritative execution plan](m4b_execution_plan.md)
- [Gate 1 packet](../../poc_llm/tests/gate1/GATE1-PACKET-001.md)
- [M0 test request](../../poc_llm/tests/m0/M0-TEST-REQUEST-001.md)

## Governing Documents

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [PM-OUT-260817-015](../pm_handoff/PM-OUT-260817-015-llm-poc-contract-plan-review.md)
- [Readiness correction](../pm_handoff/PM-POC-LLM-20260817-001-readiness-correction.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [POC workspace/Pi entry point](../../poc_llm/README.md)
