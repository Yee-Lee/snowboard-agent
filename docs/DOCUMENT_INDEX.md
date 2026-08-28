# Document Index (Income, Response, Delivery & Working Plan)

這份文件用於追蹤我們從外部團隊（PM / Core Team）收到的文件 (Income)、歷史已完成訊息 (Income History)、內部技術確認 (Response)、我們要交付給外部團隊的文件 (Delivery)，以及內部執行計畫 (Working Plan)。

## 1. Income (位於 `docs/pm_handoff/`)
這些文件是從外部接收的任務、合約與需求，對本團隊為**嚴格唯讀 (Read-only)**：

* [`DELIVERY-LLM-POC-M4B-CONTRACT-001.md`](pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md) - Core Designer M4b contract，2026-08-19 Gate 1 x86＋產品Pi compatibility revision
* [`DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001.md`](pm_handoff/DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001.md) - Core接受cumulative boundary、R3 replacement SHA與execution；Gate 1 closure仍待completed manifest review
* [`DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md`](pm_handoff/DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md) - Core接受四份P6.1/P7.1 receipts、Qwen defect waiver與雙candidate Gate 2A entry；Gate 1 closed
* [`core_llm_m4b_tasks.md`](pm_handoff/core_llm_m4b_tasks.md) - M4b LLM 任務需求與邊界規範

## 2. Income History (位於 `docs/pm_handoff/history/`)
已完成處理、被新合約取代或不再處於活動狀態的 handoff 訊息，歸檔於此，**代表已完成不必重複追蹤**：

* `DELIVERY-014-CORE-LLM-POC-PACKETS-ACK.md` - (被取代) 由 016 取代
* `RESP-LLM-POC-PI-EXECUTION-PACKETS-001.md` - (被取代) 由 002 取代
* `DELIVERY-015-CORE-P9-SURROGATE-ACK.md` - (已完成) Core 接受 P9 surrogate
* `RESP-LLM-POC-P9-SURROGATE-EXECUTABLE-001.md` - (已完成) M4A-P9 整合解除封鎖
* `DELIVERY-AUDIO-POC-M3-ACK-001.md` - (歷史) Audio M3 HAL 合約採用確認
* `core_audio_m3_requirements.md` - (歷史) 舊主線 M3 音訊要求
* `audio_poc_delivery_checklist.md` - (歷史) 舊 Audio 交付清單
* `audio_poc_development_guide.md` - (歷史) 舊 Audio 開發指引
* `PM-OUT-260817-015-llm-poc-contract-plan-review.md` - (已解決) Core contract / plan review 原始 brief
* `DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md` - (已關閉) `OUT-M4B-2026-007` revision request
* `DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md` - (已關閉) `007-A～D` revision request
* `PM-POC-LLM-20260817-001-readiness-correction.md` - (已完成) Gate 0/M0 readiness correction
* `DELIVERY-LLM-POC-M4B-GATE0-R2-ACK-001.md` - (已完成) Gate 0 R2 Final ACK
* `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001.md` - (已完成) Gate 1 platform revision 授權；已由 packet R4 承接
* `DELIVERY-LLM-POC-M4B-GATE1-PACKET-R4-ACK-001.md` - (已完成) Gate 1 Packet Revision 004 acceptance
* `commit_workflow_update.md` - (已納入) Candidate Commit 與 append-only 原則已整合至 repo workflow
* `DELIVERY-LLM-POC-M1-FREEZE-REVISION-001.md` - (已取代) R1 四項 finding 已由 Revision 002 收斂為單一 FATAL blocker
* `DELIVERY-LLM-POC-M1-FREEZE-REVISION-002.md` - (已關閉) R3 exact SHA 已獲 Core Designer freeze approval
* `ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001.md` - (已承接) design/preparation授權已由 ARM64 diagnostic ACK推進為bounded continuation
* `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001.md` - (已承接) ARM64 diagnostic/WIP 授權已由 ARM64-to-Pi transition ACK取代
* `REQUEST-LLM-POC-P9-SURROGATE-ENVELOPE-001.md` - (已回覆) Core Designer 要求提供 M4A-P9 資源保留 surrogate envelope
* `PM-POC-LLM-20260818-002-litert-lm-candidate-research-reference.md` - (已納入) 候選與Pi規劃已由formal candidate freeze及實測取代
* `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001.md` - (已承接) platform-config revision已納入後續cumulative R3 design
* `ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001.md` - (已完成) ARM64到Pi transition與candidate freeze已執行
* `DELIVERY-016-CORE-LLM-POC-PACKETS-ACK-R2.md` - (已取代) 舊physical-Pi packet delivery已由cumulative R3 ACK取代
* `RESP-LLM-POC-PI-EXECUTION-PACKETS-002.md` - (已取代) 舊packet source disposition已由cumulative R3 ACK取代

## 3. Response (位於 `docs/response/`)
POC 團隊內部的技術確認、評估結果或對外部 Income 的技術 ACK：

* [`ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/response/ACK-DELIVERY-LLM-POC-M4B-CONTRACT-001.md) - M4b 合約內部技術審查與 12 項測試指標承接確認
* [`RESP-POC-LLM-READINESS-2026-001.md`](response/RESP-POC-LLM-READINESS-2026-001.md) - 逐 finding 修訂回覆；Team revised 不代表 PM/Core 已關閉 finding
* [`RESP-PM-OUT-260817-015.md`](response/RESP-PM-OUT-260817-015.md) - 015 複驗回覆、changed paths 與 remaining Core decisions
* [`RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md`](response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001.md) - OUT-M4B-2026-007 fail-closed packet 修正與複驗回覆
* [`RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md`](response/RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002.md) - 007-A～D authenticated fail-closed packet 修正與複驗回覆
* [`RESP-DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001.md`](response/RESP-DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001.md) - Gate 1 platform ACK intake、requirement mapping與revision-004 verification
* [`ACK-LLM-M2-GATE1-PLATFORM-CONFIG-R5-INTAKE-001.md`](response/ACK-LLM-M2-GATE1-PLATFORM-CONFIG-R5-INTAKE-001.md) - Core R5 platform-config ACK intake、scope mapping與exact-SHA review status
* [`RESP-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001.md`](response/RESP-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001.md) - ARM64/x86_64 UTM bounded offline preflight內部評估、固定平台裁決與執行邊界
* [`RESP-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001.md`](response/RESP-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001.md) - Core ARM64 exception acceptance與bounded WIP continuation intake
* [`ACK-M1-FROZEN-CONTRACT-001.md`](response/ACK-M1-FROZEN-CONTRACT-001.md) - M1 locked PromptBuilder、wire protocol、strict-config Freeze Candidate；單次 Designer/Tester review pending
* [`RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-001.md`](response/RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-001.md) - M1 replacement candidate 對 `M1-FREEZE-001～004` 的實作與 executable proof 對照
* [`RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-002.md`](response/RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-002.md) - FATAL child-wire terminal guard、六類 direct regression 與 R3 exact candidate 回覆
* [`ACK-DELIVERY-LLM-POC-M1-FREEZE-R3-001.md`](response/ACK-DELIVERY-LLM-POC-M1-FREEZE-R3-001.md) - Core repo Designer freeze ACK intake；同一 SHA Internal Tester sign-off pending
* [`ACK-INTERNAL-TESTER-M1-SIGNOFF-001.md`](response/ACK-INTERNAL-TESTER-M1-SIGNOFF-001.md) - Internal Tester M1 exact candidate/deterministic evidence sign-off
* [`ACK-DELIVERY-AUDIO-POC-M3-001.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/response/ACK-DELIVERY-AUDIO-POC-M3-001.md) - (歷史) Audio M3 HAL 採用存檔確認
* [`RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001.md`](response/RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001.md) - M4A-P9 資源保留 surrogate envelope 估算回覆
* [`ACK-LLM-M2-GATE1-PI-COMPAT-006-REVIEW-001.md`](response/ACK-LLM-M2-GATE1-PI-COMPAT-006-REVIEW-001.md) - 更正v6為READY計時packet defect；撤回candidate FAIL／zero-finalist解讀
* [`ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001.md`](response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001.md) - Gate 1/2A/2B累積P1–P12分工、去重與identity carry-forward評估
* [`REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-001.md`](response/REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-001.md) - 已由R2取代的初次review request
* [`ACK-LLM-M2-CUMULATIVE-GATES-REVIEW-001.md`](response/ACK-LLM-M2-CUMULATIVE-GATES-REVIEW-001.md) - 已由Reviewer後續overwrite findings取代；不得作execution approval
* [`REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-R2-001.md`](response/REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-R2-001.md) - 已獲APPROVE；回覆source-SHA recursive invalidation與P5 fast-model兩項blocker
* [`ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE.md`](response/ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE.md) - Reviewer無條件`APPROVE` R2；兩項critical findings關閉，可發布reviewed source
* [`REVIEW-REQUEST-LLM-M2-GATE1-TARGET-UNIT-R3-001.md`](response/REVIEW-REQUEST-LLM-M2-GATE1-TARGET-UNIT-R3-001.md) - Pi pure test發現same-tick negative-fixture nondeterminism；R3只改test+lock，User已免除targeted re-review並授權繼續
* [`ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-20260827-USER-REVIEW.md`](response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-20260827-USER-REVIEW.md) - 已於發布前撤回；legacy P6/P7不再產生credit，等待P6.1/P7.1 replacement evidence
* [`ASSESSMENT-LLM-M2-GATE1-RUNNER-EXECUTION-LESSONS-001.md`](response/ASSESSMENT-LLM-M2-GATE1-RUNNER-EXECUTION-LESSONS-001.md) - P1.1、Engine lifecycle、artifact receipt、Pi operator與Gate 2/product影響紀錄
* [`ASSESSMENT-LLM-M2-GATE1-P6.1-P7.1-20260827-USER-REVIEW.md`](response/ASSESSMENT-LLM-M2-GATE1-P6.1-P7.1-20260827-USER-REVIEW.md) - 四份獨立reboot replacement receipts；P6.1雙PASS、Gemma P7.1 PASS、Qwen P7.1 SLOW_RECOVERY/FAIL，待User裁決
* [`ASSESSMENT-LLM-M3-GATE2A-ENTRY-AUDIT-001.md`](response/ASSESSMENT-LLM-M3-GATE2A-ENTRY-AUDIT-001.md) - Gate 2A進場稽核與worktree remediation；002 runner/lock已通過workstation驗證，待review/commit/Pi execution
* [`REVIEW-REQUEST-LLM-M3-GATE2A-EXECUTABLE-002.md`](response/REVIEW-REQUEST-LLM-M3-GATE2A-EXECUTABLE-002.md) - Gate 2A 002 executable worktree reviewer入口、resolved findings、exact surface與核對清單
* [`REVIEW-REQUEST-LLM-M4-GATE2B-EXECUTABLE-001.md`](response/REVIEW-REQUEST-LLM-M4-GATE2B-EXECUTABLE-001.md) - Gate 2B real Audio→LLM→Audio executable、Accepted Audio identity、resource/cleanup核對清單

## 3A. Independent Reviews (位於 `docs/reviews/`)

* [`REVIEW-LLM-M2-CUMULATIVE-REDESIGN-001.md`](reviews/REVIEW-LLM-M2-CUMULATIVE-REDESIGN-001.md) - R2前的兩項critical findings；已由R2 approval關閉，保留審查歷程
* [`REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-001.md`](reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-001.md) - 依User縮限POC範圍後的Gate 2 executable獨立審查；五項有效性與failure-path findings待一次修正
* [`REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R2-001.md`](response/REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R2-001.md) - F1～F5單輪replacement、兩層lock與targeted re-review入口；Pi尚未授權
* [`REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R2-001.md`](reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R2-001.md) - R2 targeted re-review；F1/F5關閉，P5原子transition、實際runner錯誤分類與partial-start cleanup仍為blocking
* [`REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R3-001.md`](response/REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R3-001.md) - 僅回覆R2-F1～F3；P5仲裁、post-READY typed runner path與partial-start owner cleanup replacement
* [`REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R3-001.md`](reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R3-001.md) - R3 targeted review；partial-start已關閉，native cancel lifetime與scored exception precedence仍blocking
* [`REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R4-001.md`](response/REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R4-001.md) - 僅回覆R3-F1/F2；Condition lifetime、post-call marker、exception matrix與two-stage disposition
* [`REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R4-001.md`](reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R4-001.md) - R4 targeted approval；R3-F1/F2已關閉，exact milestone commit/push已授權，Pi仍未授權

## 4. Delivery (位於 `docs/delivery/`)
我們要對外正式交付給外部團隊（由 PM 轉交）的文件，命名規範為 `DELIVERY-{流水號}-{to_who}-{title}.md`：

* [`DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md`](file:///Users/yee/Workspace/poc_llm/snowboard-agent/docs/delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md) - 回覆 `DELIVERY-LLM-POC-M4B-CONTRACT-001` 的 Gate 0 簽收回條與 Initial Manifest
* [`DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST.md`](delivery/DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST.md) - 請 Core 核准 Gate 1 以 Ubuntu x86_64 完整初篩，最多兩個候選再於產品 Debian Pi 執行 bounded compatibility try-run
* [`DELIVERY-003-PM-LLM-POC-GATE1-PACKET-R4.md`](delivery/DELIVERY-003-PM-LLM-POC-GATE1-PACKET-R4.md) - Revision 004 packet/schema/selector deterministic return；exact SHA於commit後另行提供
* [`DELIVERY-004-PM-LLM-POC-M1-FREEZE-CANDIDATE.md`](delivery/DELIVERY-004-PM-LLM-POC-M1-FREEZE-CANDIDATE.md) - M1 locked PromptBuilder/response/protocol/strict-config Freeze Candidate；請 Core Designer/Internal Tester 一次整包 review
* [`DELIVERY-005-PM-LLM-POC-M1-FREEZE-CANDIDATE-R2.md`](delivery/DELIVERY-005-PM-LLM-POC-M1-FREEZE-CANDIDATE-R2.md) - 對 Core 四項 findings 的單一 replacement；review target `llm` / `93b34c14...`
* [`DELIVERY-006-PM-LLM-POC-M1-FREEZE-CANDIDATE-R3.md`](delivery/DELIVERY-006-PM-LLM-POC-M1-FREEZE-CANDIDATE-R3.md) - locked-scope FATAL replacement；review target `llm` / `830d0b4e...`
* [`DELIVERY-007-PM-LLM-POC-M2-GATE1-PLATFORM-CONFIG-CHANGE-REQUEST.md`](delivery/DELIVERY-007-PM-LLM-POC-M2-GATE1-PLATFORM-CONFIG-CHANGE-REQUEST.md) - Gate 1 x86/Pi strict-config identity finding；請 Core 發出 replacement schema/lock/runner packet
* [`DELIVERY-008-PM-LLM-POC-M2-GATE1-R5-REVIEW.md`](delivery/DELIVERY-008-PM-LLM-POC-M2-GATE1-R5-REVIEW.md) - R5 immutable SHA review request；因實際 runner topology 新發現，由 DELIVERY-009 要求暫緩裁決
* [`DELIVERY-009-PM-LLM-POC-M2-DUAL-UTM-PREFLIGHT.md`](delivery/DELIVERY-009-PM-LLM-POC-M2-DUAL-UTM-PREFLIGHT.md) - 請 Core 先核准 ARM64/x86_64 UTM bounded preflight與固定平台選擇規則
* [`DELIVERY-010-PM-LLM-POC-M2-ARM64-PREFLIGHT-DIAGNOSTIC-REVIEW.md`](delivery/DELIVERY-010-PM-LLM-POC-M2-ARM64-PREFLIGHT-DIAGNOSTIC-REVIEW.md) - (已核准) ARM64 diagnostic exception acceptance與 ARM64/x86_64 bounded WIP continuation
* [`DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION.md`](delivery/DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION.md) - (已核准) ARM64 UTM sanitized experience kit、x86 waiver與後續移轉產品Pi的scope adjustment
* [`DELIVERY-012-PM-LLM-POC-P9-SURROGATE-EXECUTABLE.md`](delivery/DELIVERY-012-PM-LLM-POC-P9-SURROGATE-EXECUTABLE.md) - 修正 Core P9 範例缺少CPU trigger的缺陷；交付locked executable、protocol schema、process-group cleanup與Audio integration sequence
* [`DELIVERY-013-PM-LLM-POC-PI-EXECUTION-PACKETS-REVIEW.md`](delivery/DELIVERY-013-PM-LLM-POC-PI-EXECUTION-PACKETS-REVIEW.md) - Gate 1 Pi compatibility與獨立Gate 2A Pi packet的可執行review candidate；請Core一次審核packet、保留Gate 1 finalist ACK邊界
* [`DELIVERY-015-PM-LLM-POC-CUMULATIVE-GATE-DESIGN.md`](delivery/DELIVERY-015-PM-LLM-POC-CUMULATIVE-GATE-DESIGN.md) - 已由cumulative R3 ACK接受累積gate boundary、v7 logic與v6 supersession
* [`DELIVERY-016-PM-LLM-POC-GATE1-R3-TARGET-UNIT-HOLD.md`](delivery/DELIVERY-016-PM-LLM-POC-GATE1-R3-TARGET-UNIT-HOLD.md) - 要求Core暫勿ACK/execute R2 SHA；R3 targeted review後另送replacement exact SHA
* [`DELIVERY-017-PM-LLM-POC-GATE1-R3-REPLACEMENT-SHA.md`](delivery/DELIVERY-017-PM-LLM-POC-GATE1-R3-REPLACEMENT-SHA.md) - 已送Core；R3 SHA `4dc76d1…`與surface `568aa7…dc5`已獲cumulative R3 ACK
* [`DELIVERY-018-PM-LLM-POC-GATE1-CLOSURE.md`](delivery/DELIVERY-018-PM-LLM-POC-GATE1-CLOSURE.md) - User已裁決；請Core一次接受四份replacement receipts、Gate 1 PASS及Qwen P7.1 defect waiver
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
* [`GATE1-ENV-PREFLIGHT-ARM64-001.md`](../poc_llm/tests/gate1/GATE1-ENV-PREFLIGHT-ARM64-001.md) - ARM64-only UTM executable request；與 x86_64 package/evidence 隔離
* [`GATE1-ENV-PREFLIGHT-ARM64-001-DIAGNOSTIC-001.md`](../poc_llm/tests/gate1/GATE1-ENV-PREFLIGHT-ARM64-001-DIAGNOSTIC-001.md) - User-authorized ARM64 diagnostic `PASS` 與 formal change-review boundary
* [`GATE1-PI-COMPAT-PACKET-007.md`](../poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md) - `DESIGN REVIEW`；Pi 5累積P1/P6/P7/P10A/P11/P12 executable packet
* [`GATE1-P6.1-P7.1-REDESIGN-001.md`](../poc_llm/tests/gate1/GATE1-P6.1-P7.1-REDESIGN-001.md) - legacy P6/P7 replacement；官方async cancel與獨立force-abort/rebuild設計，待User source review後執行
* [`GATE2A-PI-PACKET-002.md`](../poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md) - 只執行Gate 1未涵蓋的P2/P3/P4/P5/P8
* [`GATE2B-PI-PACKET-001.md`](../poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md) - Accepted Audio整合的P9/P10B及affected-only regression
* [`env-preflight-arm64-001.json`](../poc_llm/evidence/gate1/env-preflight-arm64-001.json) - ARM64 sanitized attempt history、checksums與結果範圍
