# LLM POC Milestone and Contract Gate Index

本檔是External Gate、internal milestone、目前授權與風險的唯一狀態入口。

最後更新：2026-08-28

## Current reachability

狀態：`GATE1 CLOSED / GATE2 DEVELOPMENT READINESS APPROVED / SOURCE FROZEN FOR DELIVERY / PI NOT AUTHORIZED`。

Gate 0與M1已完成。ARM64 UTM只作工程輸入；Gemma 4 E2B與Qwen2.5 1.5B為固定Pi inputs。
歷史`G1-PI-COMPAT-006` run永久保留，但其READY clock錯誤包含完整模型SHA，定性為packet defect，
不淘汰candidate、不產生P credit。User已取消「Gate 1不得產生P1～P12 credit」的本地規則，改採
Gate 1/2A/2B累積矩陣。該階段Reviewer回覆要求修正source-SHA遞迴失效與P5 fast-model trap；
R2已改用execution-surface digest與continuous-timeout fixture；Reviewer已無條件APPROVE，現先發布
R2 source `b5690bbbef50ce37af356fd29b88ab920207c38e`已push/送Core，但Pi pure test在任何operator
change/model load前發現same-tick negative-fixture nondeterminism。R3只修test+lock，workstation
25/25、Pi isolated 14/14；Core已hold R2 SHA。User明確免除test-only targeted re-review，
R3 exact SHA `4dc76d1574daa7a9f7f56b98a8d65e00258fd46c`與surface `568aa7…dc5`
已push且獲Core ACK。其後append-only runs保留P1/P10A/P11/P12等有效工程證據；但官方
LiteRT-LM v0.16 source review證明舊P6未使用documented async path，且舊P7承接cancel-conditioned
process。舊P6/P7 credit與closure draft已撤回，User核准獨立P6.1/P7.1 prospective redesign。

## External gates

| Gate | State | First-executed P items | Close condition / next action |
| --- | --- | --- | --- |
| Gate 0 | `COMPLETE` | none | retained receipt |
| Gate 1 | `CLOSED / CORE ACK` | P1, P6.1, P7.1, P10A, P11, P12 | accepted receipts；Gemma finalist＋Qwen defect waiver |
| Gate 2A | `DEVELOPMENT READINESS APPROVED / NOT_STARTED` | P2, P3, P4, P5, P8 | R4已關閉R3-F1/F2；待pushed exact SHA、Pi授權與staging |
| Gate 2B | `DEVELOPMENT READINESS APPROVED / NOT_STARTED` | P9, P10B | R4已關閉shared scored boundary；待Gate 2A receipt、Pi授權與staging |
| Gate 3 | `OUT_OF_POC_SCOPE` | Core tests | Core production acceptance |

只有指定Reviewer/User/Core可以關閉其review/approval；POC self-test不等於external ACK。

## Internal milestones

| Milestone | State | Summary |
| --- | --- | --- |
| M0 | `COMPLETE` | readiness execution/review complete |
| M1 | `COMPLETE` | frozen candidates/contract harness signed off |
| M2 | `COMPLETE` | Core closed Gate 1；Gemma normal finalist；Qwen P7.1 FAIL且依defect waiver保留Gate 2A資格 |
| M3 | `NOT_STARTED` | Development readiness已通過R4 review；待pushed exact SHA與Pi授權後才可改為`IN_PROGRESS` |
| M4 | `NOT_STARTED` | Development readiness已通過R4 review；待Gate 2A receipt、Pi授權與staging |

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

- **Qwen P7.1 defect**：rebuild READY `18152.025 ms`，維持`FAIL / SLOW_RECOVERY`；User保留其
  Gate 2A candidate資格尋求workaround，但不得把waiver改寫為PASS。
- **Core closure ACK**：`DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001`已接受四份replacement
  receipts、User Qwen defect waiver、兩名Gate 2A candidates並關閉Gate 1。
- **Pi operator state**：Gate 1後已恢復zram/network、移除`/tmp` bind且無殘留process；模型仍在
  `/var/tmp`持久保存。Gate 2A需重新建立read-only staging並重做clean/offline/swap preflight。
- **P1 startup**：Gemma 1024與Qwen 512皆通過initial READY；capacity必須綁exact artifact，禁止恢復
  implicit 4096 default或把144-token protocol envelope當Engine capacity。
- **P6**：native cancel已知可能nondeterministic；只有P7完整PASS才允許Conditional escalation。
- **P4**：完整方法未達negotiable target需Core written decision。
- **P5**：固定continuous 512-token chunks共用單一outer timer；chunk完成固定CONTINUE，禁止
  early RESULT及結果後adaptive fixture。
- **Gate 2 R4 review**：R3-F1/F2已關閉；Condition lifetime、post-call outcome、窄typed boundary、
  primary-before-rebuild及runner/verifier一致性均通過可重複實驗。Reviewer授權exact
  milestone commit/push；Pi execution、benchmark publication與candidate proposal仍未授權。
- **Accepted Audio**：Audio annotated tag `audio_m4`（tag object `24b2571a…`）指向accepted completion
  `5694ead4…`與Core acceptance
  `RESP-AUDIO-M4-GATE2B-001` / `be19b70b…`已確認；Pi上實體artifact staging與LLM combined
  runner replacement已在worktree完成且Gate 2 suite 59/59；Pi實體artifact staging與execution
  authorization仍待完成，不把
  既有Audio-only PASS誤作M4B P9/P10B credit。
- **Evidence safety**：不commit model、wheel、native binary、raw output、prompt/payload、credential或endpoint。

## Active packets

- [Gate 1 cumulative packet](../../poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md)
- [Gate 1 P6.1/P7.1 corrective packet](../../poc_llm/tests/gate1/GATE1-P6.1-P7.1-REDESIGN-001.md)
- [Gate 2A remaining packet](../../poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md)
- [Gate 2B combined packet](../../poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md)
- [Cumulative redesign assessment](../response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-REDESIGN-001.md)
- [Independent reviewer request](../response/REVIEW-REQUEST-LLM-M2-CUMULATIVE-GATES-001.md)
- [Latest Gate 2 reviewer decision](../reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R4-001.md)
- [R2 reviewer approval](../response/ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE.md)
- [Gate 1 cumulative User review](../response/ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-20260827-USER-REVIEW.md)
- [Gate 1 P6.1/P7.1 User review](../response/ASSESSMENT-LLM-M2-GATE1-P6.1-P7.1-20260827-USER-REVIEW.md)
- [Gate 1 runner lessons](../response/ASSESSMENT-LLM-M2-GATE1-RUNNER-EXECUTION-LESSONS-001.md)
- [Gate 2A entry audit](../response/ASSESSMENT-LLM-M3-GATE2A-ENTRY-AUDIT-001.md)
- [Gate 1 closure delivery draft](../delivery/DELIVERY-018-PM-LLM-POC-GATE1-CLOSURE.md)

## Governing and historical inputs

2026-08-28 round-close audit：`docs/pm_handoff/`四份直屬Income均仍具治理效力。M4b
contract與Core task boundary控制最終交付；cumulative R3 ACK控制跨gate累積與
carry-forward；Gate 1 closure ACK控制兩名Gate 2A candidate及Qwen waiver。本輪無檔案可歸檔。

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Pi packet R2 ACK (historical)](../pm_handoff/history/RESP-LLM-POC-PI-EXECUTION-PACKETS-002.md)
- [Cumulative Gate R3 ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001.md)
- [Gate 1 closure ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md)
- [ARM64-to-Pi transition ACK (historical)](../pm_handoff/history/ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [Pi entry point](../../poc_llm/README.md)
