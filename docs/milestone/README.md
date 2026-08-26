# LLM POC Milestone and Contract Gate Index

本檔是External Gate、internal milestone、目前授權與風險的唯一狀態入口。

最後更新：2026-08-26

## Current reachability

狀態：`GATE1_R2_REVIEW_APPROVED / PUBLISHING REVIEWED SOURCE`。

Gate 0與M1已完成。ARM64 UTM只作工程輸入；Gemma 4 E2B與Qwen2.5 1.5B為固定Pi inputs。
歷史`G1-PI-COMPAT-006` run永久保留，但其READY clock錯誤包含完整模型SHA，定性為packet defect，
不淘汰candidate、不產生P credit。User已取消「Gate 1不得產生P1～P12 credit」的本地規則，改採
Gate 1/2A/2B累積矩陣。Reviewer最新回覆要求修正source-SHA遞迴失效與P5 fast-model trap；
R2已改用execution-surface digest與continuous-timeout fixture；Reviewer已無條件APPROVE，現先發布
reviewed source/exact SHA，再送Core並執行Pi。

## External gates

| Gate | State | First-executed P items | Close condition / next action |
| --- | --- | --- | --- |
| Gate 0 | `COMPLETE` | none | retained receipt |
| Gate 1 | `REVIEW APPROVED / PUBLISHING` | P1, P6, P7, P10A, P11, P12 | reviewed-source commit/push→Pi run→User result review→Core cumulative/finalist ACK |
| Gate 2A | `REDESIGNED / NOT_STARTED` | P2, P3, P4, P5, P8 | consume Gate 1 receipt；最多1 provisional finalist |
| Gate 2B | `BLOCKED` | P9, P10B | Accepted Audio kit + 4GB combined PASS；Core final winner ACK |
| Gate 3 | `OUT_OF_POC_SCOPE` | Core tests | Core production acceptance |

只有指定Reviewer/User/Core可以關閉其review/approval；POC self-test不等於external ACK。

## Internal milestones

| Milestone | State | Summary |
| --- | --- | --- |
| M0 | `COMPLETE` | readiness execution/review complete |
| M1 | `COMPLETE` | frozen candidates/contract harness signed off |
| M2 | `REVIEW APPROVED / PUBLISHING` | Gate 1 `007`：正式P1/P6/P7/P10A/P11/P12；準備exact SHA與Pi execution |
| M3 | `REDESIGNED / NOT_STARTED` | Gate 2A `002`：只補P2/P3/P4/P5/P8 |
| M4 | `REDESIGNED / BLOCKED` | Gate 2B `001`：P9/P10B；缺Accepted Audio |

## Cumulative P1～P12 rule

- Gate 1 accepted evidence：P1/P6/P7/P10A/P11/P12。
- Gate 2A accepted evidence：P2/P3/P4/P5/P8。
- Gate 2B accepted evidence：P9/P10B。
- Execution commit為ancestor且execution-surface lock、runtime/model/config/protocol/fixture、
  Pi/environment及manifest identity相同時不重跑；evidence/docs commit不造成失效。
- Drift只使affected item失效；gate transition本身不構成rerun理由。
- P5只在Pi的2A執行；P9/P10B只用Accepted Audio正式kit，surrogate無credit。

詳細方法見[Execution Plan](m4b_execution_plan.md)與[Traceability](m4b_traceability_crosswalk.md)。

## Open dependencies and risks

- **Reviewer gate**：`ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE`已無條件關閉兩項finding；
  reviewed execution surface不得再修改，發布後才可執行。
- **Core cumulative ACK**：User允許Reviewer後execution與Core review並行，但Core ACK前不得finalize
  P credit、Gate 1 finalists或gate closure。
- **Pi operator state**：模型已在`/var/tmp`持久保存；正式run需clean exact checkout、read-only model
  staging、`swap=0`及offline interface changes，結束後恢復。
- **P1 startup**：修正後10秒只包含small receipt/config validation與Engine init；若仍超時才是正式P1 FAIL。
- **P6**：native cancel已知可能nondeterministic；只有P7完整PASS才允許Conditional escalation。
- **P4**：完整方法未達negotiable target需Core written decision。
- **P5**：固定continuous 512-token chunks共用單一outer timer；chunk完成固定CONTINUE，禁止
  early RESULT及結果後adaptive fixture。
- **Accepted Audio**：Gate 2B仍缺Core-recorded final handoff ID/SHA/executable kit。
- **Evidence safety**：不commit model、wheel、native binary、raw output、prompt/payload、credential或endpoint。

## Active packets

- [Gate 1 cumulative packet](../../poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md)
- [Gate 2A remaining packet](../../poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md)
- [Gate 2B combined packet](../../poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md)
- [Cumulative redesign assessment](../response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001.md)
- [Independent reviewer request](../response/REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-001.md)
- [Latest reviewer findings](../reviews/REVIEW-LLM-M2-CUMULATIVE-REDESIGN-001.md)
- [R2 reviewer approval](../response/ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE.md)

## Governing and historical inputs

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Pi packet R2 ACK](../pm_handoff/RESP-LLM-POC-PI-EXECUTION-PACKETS-002.md)
- [ARM64-to-Pi transition ACK](../pm_handoff/ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [Pi entry point](../../poc_llm/README.md)
