---
requestor: "Designer"
owner: "Tester"
status: "Open"
severity: "Blocking"
activation: "Deferred until M4B-MVA-POC released"
---

# TR_spec_M4B_IV — MVA automatic policy and manual semantic coverage

日期：2026-09-05。這是spec revision request，非Tester執行新Pi驗收的要求。
依據：[M4B-MVA設計](../implement/ch_m4b_llm_production.md)；
Architecture仍待[AR_impl_M4B_I](AR_impl_M4B_I.md)。
本單是Designer預備handoff；Tester不得提前寫draft或執行。依USER七步流程，
Designer審核POC並解除[M4B-MVA-POC](../milestones/M4B_MVA.md)後才進場。
現有test_spec_M4.md與candidate cards是R1驗收，不能用它们替M4B-MVA宣告PASS。

## One coordinated revision

| Existing Test IDs / scope | Required replacement / addition |
| :--- | :--- |
| CFG / LOCK / PKG | new Core profile identity；舊POC config只作provenance；移除8/48；immutable-install快路徑與identity drift拒絕 |
| IPC / RDY | snowboard.llm/2 session control、version/schema/session/request identity；optional measured prewarm；no-user-context READY |
| GEN / HIST | 同session多turn一個Conversation；close後新session隔離；不是每turn create/close計數 |
| OUT | injected semantic text/end→Reasoner action/next_perceptions；M4無real tool quality gate |
| P5 / CAN | 未改state的fallback與dirty-session end分開；typed join/cancel/close；no-THINK與所有exit routes |
| REC / RES | capacity-based trigger；自然20-session soak不強制8/16/三generation；受控recovery另驗；完整10秒目標 |
| PRIV / OFF | session memory只在private memory/pipe；新wire無private logs；網路禁止與M4A contract不變 |
| INH | lifecycle/prompt/output/token/cold-hot parity；POC raw TTFT不冒稱M4 audible latency |
| M4 integration | speech end→meaningful audible onset；相同timebase；ASR call、PCM write不代替端點 |
| Human semantic rows | 身分、基本知識、能力誠實、追問連續、結束意圖；無keyword/LLM-judge假綠燈 |

## Required regression shape

以設計§9為table-driven最低behavior集合；不要求每finding獨立test function。
至少注入：normal/end/unavailable、input too large/capacity full、invalid output/timeout/cancel、
session end without THINK、interrupt during open/close、late old-session terminal、
memory plateau/low capacity/replacement still low、trust drift、no-waiter recovery failure。
逐列列expected status/exit、禁止artifact或Fact、cleanup和identity assertion。
保留既有M4A shared-path regression，不無差別重驗Accepted M4A-only target rows。

## Human evidence / performance

Runtime語意只由real output依rubric人工判定，mock不算knowledge/continuity證據。
既有card/report記run_id、case_id、operator、時間、五類rubric各Pass/Fail、
sanitized reason、timing；不保存private raw prompt/answer/audio。
Public catalog與expected semantic rubric可tracked；未用於prompt調整的holdout由評估者保管。
不得要求exact示範答案；錯誤或fallback回答不算normal latency PASS。
性能原始結果與quality判斷分欄；計量誤差、缺樣本標Invalid/Incomplete而非PASS。

3秒／10秒是當前可修訂目標，miss記錄與後續profile/USER裁決，不自動變成no-go。
Designer須在gate解除前採用input/output/memory/watchdog值；Tester進場後依
已採用profile完成單次spec delta，不臆填尚未定案值。
同步tests/m4b_target_cases.py、scripts/candidate_gate.py的固定counter/card要求、
m4b_target_metrics/inheritance與catalog；由Developer實作，不由Tester改product code。

## Completion

Owner將spec及trace修訂後標Revised，Designer核對automation/manual coverage與profile一致性；
Resolved前不建立M4B-MVA candidate。這不回退M4A Accepted，不重標歷史TR_spec或r14 evidence。
