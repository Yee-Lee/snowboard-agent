# LLM POC Milestone and Contract Gate Index

本檔是 LLM POC 外部 Contract Gate、內部 execution milestone、目前授權範圍與
風險的唯一狀態入口。External Gate 由合約 owner/recorder 關閉；Internal Milestone
由 POC workflow 的 entry/exit review 控制，兩者不得共用狀態。

最後更新：2026-08-23

## Current Delivery Reachability

最終交付可達性：`GATE0_R2_COMPLETE_M1_COMPLETE`。

Core Designer 已複驗 `llm` / `0d415d174390665ed92793937d30334f01e3df14`，
關閉 `OUT-M4B-2026-007-A～D`，並正式登錄 Gate 0 R2 `COMPLETE`。PM handoff 015
已解決；此 ACK 僅接受 planning/regression packet，不代表已執行 Ubuntu benchmark、
Pi run 或 candidate evidence。R5 exact-SHA review request 因實際可用 runner 均為 UTM，
已暫緩。Core 已接受 `265db05776b6bf5fadca5b3c3ab41345aa68819e` 為完整 ARM64
diagnostic/change record，例外接受其 formal environment-preflight `PASS` 並選 ARM64 為 primary。
ARM64/x86_64 WIP branches 已獲 bounded continuation 授權；兩次先前 runner-defect
`INCONCLUSIVE` 永久保留，x86_64 作為獨立 portability/fallback且不阻擋 ARM64。

## External Contract Gates

| Gate | 狀態 | Owner / recorder or approver | 關閉條件 | 下一個允許動作 |
| --- | --- | --- | --- | --- |
| **Gate 0** Contract Receipt | `COMPLETE` | POC Team 提交；PM 收件；Core Designer 已登錄 | `0d415d...` 複驗通過；OUT-M4B-2026-007-A～D 已關閉 | 進行 M0 entry review；不自動啟動 M0 |
| **Gate 1** Candidate Proposal, environment preflight, pre-screen & Pi Compatibility | `NOT_STARTED / BLOCKED` | POC Team 提交；Core Designer 書面確認 | ARM64 primary與x86_64 portability/fallback各自完成bounded workstation scope；之後產品Pi compatibility只保留`PASS`且不補位 | 兩個 WIP tracks依predeclared commands/stop conditions推進；雙方回報且Technical Lead確認merge boundary後才整合回`llm` |
| **Gate 2A** Pi 5 LLM-only | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核 | P1～P8、P10A、P11、P12 依 matrix 完成 | 只能產生 provisional finalist ACK |
| **Gate 2B** Audio+LLM combined | `NOT_STARTED / BLOCKED` | POC Team 執行；Core Designer 審核 | Accepted Audio package、P9、P10B 及固定 2A regression 全部通過 | Core Designer 才可發 final winner ACK |
| **Gate 3** Core Production | `OUT_OF_POC_SCOPE` | Core Developer / Tester / Designer | 依 Core contract | POC 僅提供 accepted handoff material |

POC Team 的 ACK、self-test 或 Technical Lead review 都不能把 External Gate 標成
`COMPLETE`；只有上表指定的 recorder/approver 可以關閉對應 Gate。

## Internal Execution Milestones

| Milestone | 狀態 | 摘要 | 依據 |
| --- | --- | --- | --- |
| **M0** | `COMPLETE` | `M0-RUN-001` 執行與審核皆完成；Internal Tester confirmed | [M0](m0_llm_readiness.md) |
| **M1** | `COMPLETE` | Frozen exact candidate 經驗證無誤；Internal Tester 完成 lock/evidence 獨立 sign-off | [M1](m1_llm_contract_and_harness.md) |
| **M2** | `PLANNED` | ARM64 primary Ubuntu pre-screen＋x86_64 portability/fallback＋產品Pi compatibility；最多保留兩個 proposed finalists | [M2](m2_llm_candidate_evaluation.md) |
| **M3** | `PLANNED` | Gate 2A：Pi 5 LLM-only P1～P8、P10A、P11、P12；provisional finalist | [M3](m3_llm_child_pi_integration.md) |
| **M4** | `PLANNED` | Gate 2B：Accepted Audio package、P9、P10B、2A regression；final winner | [M4](m4_llm_combined_validation_and_delivery.md) |

Internal M0 已完成 entry、packet execution、Technical Lead evidence review 與 Internal Tester confirmation，標示為 `COMPLETE`。M0 完成不能取代 Gate 1 Core Designer ACK。

## Delivery Taxonomy and Traceability

唯一 delivery taxonomy 為 D1–D8。External Gate、Internal Milestone、Delivery Area、
M4B-P1～P12、owner、delivery item 與 evidence 狀態的唯一 crosswalk 見
[M4b Traceability Crosswalk](m4b_traceability_crosswalk.md)。其他文件只能引用該表，
不得另建競爭映射。

## Open Dependencies, Risks and Adjustment Requests

- **Gate 1 R5 repository revision**：Core 以
  `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001` 接受
  `M2-G1-PLATFORM-CONFIG-001` 並授權 append-only `G1-X86-PI-COMPAT-005`。R5 已維持
  M1 freeze、完成 deterministic/R4/M1 retained regressions，並以 committed exact SHA
  `190a827b4c82279e4300af6075e2eeb52b91cd54` 建立 review target。因兩台可用 Ubuntu 24.04
  workstation 都是 UTM，該 review request 已暫緩。Core 已核准 ARM64/x86_64 bounded WIP
  continuation；R5 exact-SHA acceptance仍 held。兩個 branch 完成及受控整合前不得把 R5 視為
  accepted，Pi execution 和 Gate 2 仍封鎖。
- **M1 completion**：Core repo 的 `DELIVERY-LLM-POC-M1-FREEZE-R3-ACK-001` 已接受並
  freeze exact candidate `830d0b4ed2d41406c789bb110ed84b7553f330a4`。Internal Tester
  已完成同一 SHA 的 lock、self-test 與 35/35 回歸測試獨立 sign-off。M1 標示為
  `COMPLETE` 並建立 `llm_m1` tag；真實執行仍未授權。
- **Forward risk — Gate 2A swap**：M0 盤點發現 4GB Pi 配置約 2GB swap（未使用）。
  Gate 2A 的 mandatory environment 仍要求 `swap=0`；屆時需獨立授權，不在 M0 修改。
- **Dependency — Gate 1 candidate proposal**：研究參考建議以 LiteRT-LM v0.16.0
  配對 Gemma4-E2B、Qwen2.5-1.5B 與 Qwen2.5-0.5B；`G1-CANDIDATE-PREFLIGHT-001`
  已固定官方 revision、artifact/wheel SHA-256 與 Apache-2.0 metadata。Artifact/dependency
  bundle、source/archive checksum、adapter、strict config 與實體 manifest 尚未完成，
  candidate 仍只是 proposal。
- **Blocking finding — Gate 1 runner representativeness**：實際可用環境為 macOS ARM64 host /
  Ubuntu 24.04 ARM64 UTM guest，以及 macOS x86_64 host / Ubuntu 24.04 x86_64 UTM guest。
  ARM64 已取得 User-authorized diagnostic `PASS`：pinned wheel、offline namespace、native
  linkage、三輪 import/lifecycle與cleanup皆通過；兩次 runner-defect `INCONCLUSIVE` 及額外
  diagnostic authorization均保留。Core 已例外接受 ARM64 formal `PASS` 並選其為 primary；
  x86_64尚無結果但只作獨立 portability/fallback，不阻擋 ARM64進度。
- **Core acceptance — ARM64 direct continuation**：review target
  `265db05776b6bf5fadca5b3c3ab41345aa68819e` 保留兩次 runner-defect `INCONCLUSIVE` 與一次
  User-authorized diagnostic `PASS`。Core 已明確 waive missing pre-execution authorization、exhausted
  rerun budget與baseline deviation，接受 formal ARM64 result且不要求 corrective rerun。
- **Approved execution — bounded UTM WIP tracks**：Core 已核准使用 pinned LiteRT-LM API wheel、dependency
  bundle 與 adapter/fake-child lifecycle 做 bounded offline preflight，不下載或載入模型、不做
  generation/performance ranking。新 disposition 允許 ARM64 primary直接推進，x86_64獨立執行。
  各 branch 可在 predeclared commands/stop conditions 下完成 approved workstation scope；identity
  drift、dirty path、network fallback、unbounded process或cleanup failure必須停止。
- **Platform decision — Gate 1**：native Ubuntu aarch64 runner 需求已由 Core 移除。
  Ubuntu 24.04 x86_64 完整初篩後一次預選最多兩名，再於產品 Debian 13 Pi 執行 bounded
  compatibility；Pi `FAIL/INCONCLUSIVE` 同 cycle 不得補測第三名。
- **Dependency — M4a**：Accepted M4a Audio HAL full SHA、owner 與取得路徑仍待提供。
- **Adjustment request — Gate 1 platform split**：Core 已以
  `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001` 批准；只授權 repository packet
  revision 與 deterministic regressions。Gate 1 Pi try-run 不計 Gate 2A credit，Gate 2A
  仍須 `swap=0`、新 packet/run/namespace 完整重跑。
- **Pending adjustment — ARM64 to product Pi transition**：User要求以已完成的ARM64 UTM
  candidate pre-screen作為主要workstation工程輸入，waive未完成的x86_64 WIP與雙branch merge
  boundary，固定Gemma/Qwen 1.5B最多兩名後把其餘mandatory gates移至產品Pi獨立重跑。
  `DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION`已記錄完整identity、結果、runner lessons
  與Pi entry checklist。Core尚未核准，因此現有M2/Gate 1狀態、Pi execution block及R5 hold不變。

## Gate 0 R2 Submission Package

- [Core Final ACK](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md)
- [Readiness correction response](../response/RESP-POC-LLM-READINESS-2026-001.md)
- [015 response](../response/RESP-PM-OUT-260817-015.md)
- [Revised Gate 0 receipt](../delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md)
- [Gate 0 initial manifest R2](../../poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md)
- [M4b traceability crosswalk](m4b_traceability_crosswalk.md)
- [Authoritative execution plan](m4b_execution_plan.md)
- [OUT-M4B-2026-007-A～D response](../response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md)
- [Gate 1 R5 replacement packet](../../poc_llm/tests/gate1/GATE1-PACKET-005.md)
- [Gate 1 R5 exact-SHA review request](../delivery/DELIVERY-008-PM-LLM-POC-M2-GATE1-R5-REVIEW.md)
- [Dual UTM preflight adjustment request](../delivery/DELIVERY-009-PM-LLM-POC-M2-DUAL-UTM-PREFLIGHT.md)
- [ARM64 preflight diagnostic review](../delivery/DELIVERY-010-PM-LLM-POC-M2-ARM64-PREFLIGHT-DIAGNOSTIC-REVIEW.md)
- [Core ARM64 diagnostic and continuation ACK](../pm_handoff/ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001.md)
- [ARM64 UTM to product Pi transition request and experience handoff](../delivery/DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION.md)
- [M0 test request](../../poc_llm/tests/m0/M0-TEST-REQUEST-001.md)

## Governing Documents

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Gate 0 R2 Final ACK (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md)
- [Gate 1 Platform Change ACK (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001.md)
- [Gate 1 Packet R4 ACK (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE1-PACKET-R4-ACK-001.md)
- [Gate 1 platform-config R5 ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001.md)
- [Dual UTM preflight plan ACK (history)](../pm_handoff/history/ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001.md)
- [ARM64 diagnostic and bounded-continuation ACK](../pm_handoff/ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001.md)
- [M1 R3 Designer ACK intake](../response/ACK-DELIVERY-LLM-POC-M1-FREEZE-R3-001.md)
- [M1 Freeze Revision 002 (history)](../pm_handoff/history/DELIVERY-LLM-POC-M1-FREEZE-REVISION-002.md)
- [M1 Freeze Revision 001 (history)](../pm_handoff/history/DELIVERY-LLM-POC-M1-FREEZE-REVISION-001.md)
- [Commit workflow update (history)](../pm_handoff/history/commit_workflow_update.md)
- [LiteRT-LM candidate research reference](../pm_handoff/PM-POC-LLM-20260818-002-litert-lm-candidate-research-reference.md)
- [PM-OUT-260817-015 (resolved history)](../pm_handoff/history/PM-OUT-260817-015-llm-poc-contract-plan-review.md)
- [Gate 0 R2 revision request (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md)
- [Gate 0 R2 Revision 002 (history)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md)
- [Readiness correction (history)](../pm_handoff/history/PM-POC-LLM-20260817-001-readiness-correction.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [POC workspace/Pi entry point](../../poc_llm/README.md)
