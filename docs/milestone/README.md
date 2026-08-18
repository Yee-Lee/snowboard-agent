# LLM POC Milestone and Contract Gate Index

本檔是 LLM POC 外部 Contract Gate、內部 execution milestone、目前授權範圍與
風險的唯一狀態入口。External Gate 由合約 owner/recorder 關閉；Internal Milestone
由 POC workflow 的 entry/exit review 控制，兩者不得共用狀態。

最後更新：2026-08-18

## Current Delivery Reachability

最終交付可達性：`GATE0_SUBMITTED_PENDING_RECORDING`。

POC Team 已完成 Gate 0 修訂包並標示為 `SUBMITTED`；此狀態在修訂 commit push 並通知
PM 時生效。PM 拉回 branch HEAD、Core Designer 完成行政登錄前，External Gate 0 不得
標示 `COMPLETE`。目前只授權文件、scaffold 與 M0 packet 的 local/fake validation；
未授權 Pi 存取、runtime/model 下載、Ubuntu candidate benchmark 或 Gate 2 Pi 驗證。

## External Contract Gates

| Gate | 狀態 | Owner / recorder or approver | 關閉條件 | 下一個允許動作 |
| --- | --- | --- | --- | --- |
| **Gate 0** Contract Receipt | `SUBMITTED` | POC Team 提交；PM 收件；Core Designer 登錄 | PM 記錄實際 branch HEAD，Core Designer 登錄 receipt；不新增技術 ACK | 等待收件；準備 Gate 1 proposal，不執行 benchmark |
| **Gate 1** Candidate Proposal & Ubuntu Pre-screen | `NOT_STARTED / BLOCKED` | POC Team 提交；Core Designer 書面確認 | 固定 pairing、license/offline/provenance preflight、Ubuntu x86/arm64 初篩及最多兩個 finalists 均完整 | Core Designer ACK 後才可進 Gate 2 |
| **Gate 2** Pi 5 Validation | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核；PM 轉達 | 核准 finalist 的 M4B-P1～P12 evidence 完整並取得 final winner ACK | 交由 Core Gate 3 產品化 |
| **Gate 3** Core Production | `OUT_OF_POC_SCOPE` | Core Developer / Tester / Designer | 依 Core contract | POC 僅提供 accepted handoff material |

POC Team 的 ACK、self-test 或 Technical Lead review 都不能把 External Gate 標成
`COMPLETE`；只有上表指定的 recorder/approver 可以關閉對應 Gate。

## Internal Execution Milestones

| Milestone | 狀態 | 摘要 | 依據 |
| --- | --- | --- | --- |
| **M0** | `NOT_STARTED` | Environment、exact SHA、command lifecycle 與 evidence-chain readiness | [M0](m0_llm_readiness.md) |
| **M1** | `PLANNED` | Freeze boundary/harness，固定 candidate pairing 與 preflight | [M1](m1_llm_contract_and_harness.md) |
| **M2** | `PLANNED` | Ubuntu x86/arm64 pre-screen，最多保留兩個 Pi finalists | [M2](m2_llm_candidate_evaluation.md) |
| **M3** | `PLANNED` | Gate 1 ACK 後的 Pi 5 M4B-P1～P12 candidate/persistent-child 驗證 | [M3](m3_llm_child_pi_integration.md) |
| **M4** | `PLANNED` | Accepted M4a SHA combined/offline/soak validation 與 Gate 2 delivery | [M4](m4_llm_combined_validation_and_delivery.md) |

Internal M0 在 entry review、test request 核准及 Pi 操作授權前保持 `NOT_STARTED`。
Gate 0 行政收件完成不會自動啟動 M0，M0 完成也不能取代 Gate 1 Core Designer ACK。

## Delivery Taxonomy and Traceability

唯一 delivery taxonomy 為 D1–D8。External Gate、Internal Milestone、Delivery Area、
M4B-P1～P12、owner、delivery item 與 evidence 狀態的唯一 crosswalk 見
[M4b Traceability Crosswalk](m4b_traceability_crosswalk.md)。其他文件只能引用該表，
不得另建競爭映射。

## Open Dependencies, Risks and Adjustment Requests

- **Blocker — Gate 0 recording**：PM 尚未拉回修訂 branch HEAD，Core Designer 尚未登錄。
- **Blocker — pending income**：`PM-OUT-260817-015` 尚未進 repo；目前 correction 狀態仍為
  `On hold`，不得據此宣告 Gate 1 已開啟。
- **Blocker — Internal M0 authorization**：Pi 5 4GB/8GB availability、operator access 與
  immutable test request 尚待 entry review；M0 仍為 `NOT_STARTED`。
- **Risk — Ubuntu arm64 availability**：Gate 1 所需 Ubuntu arm64 runner 尚未登錄；若無
  native runner，必須提出可重現替代方案並取得 Core Designer 同意，不能以 x86 結果代替。
- **Dependency — M4a**：Accepted M4a Audio HAL full SHA、owner 與取得路徑仍待提供。
- **Adjustment request**：無門檻降低請求；若硬體/runner 不可用，應記為 `Blocked` 或
  `INCONCLUSIVE`，不得改寫為通過。

## Gate 0 Submission Package

- [Readiness correction response](../response/RESP-POC-LLM-READINESS-2026-001.md)
- [Revised Gate 0 receipt](../delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md)
- [Gate 0 initial manifest](../../poc_llm/deliveries/POC-llm-DEL-2026-001-R1.md)
- [M4b traceability crosswalk](m4b_traceability_crosswalk.md)
- [M0 test request](../../poc_llm/tests/m0/M0-TEST-REQUEST-001.md)

## Governing Documents

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Readiness correction](../pm_handoff/PM-POC-LLM-20260817-001-readiness-correction.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [POC workspace/Pi entry point](../../poc_llm/README.md)
