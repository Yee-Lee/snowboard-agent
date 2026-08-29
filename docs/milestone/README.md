# LLM POC Milestone and Contract Gate Index

本檔是External Gate、internal milestone、目前授權與風險的唯一狀態入口。

最後更新：2026-08-29

## Current reachability

狀態：`GATE1 CLOSED / GATE2A POC ROUND CLOSED / GEMMA MODEL FINALIST / CORE ACK PENDING / GATE2B IN_PROGRESS`。

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
| Gate 2A | `POC ROUND CLOSED / USER SELECTED / CORE ACK PENDING` | P2, P3, P4, P5, P8 | final evidence已review；Gemma唯一model finalist；machine P2/P8 FAIL不改寫，請Core ACK語意與selection |
| Gate 2B | `USER AUTHORIZED / IN_PROGRESS` | P9, P10B | r5先通過exact-SHA static preflight及單session全鏈no-credit diagnostic；兩者通過後才允許attempt 006 |
| Gate 3 | `OUT_OF_POC_SCOPE` | Core tests | Core production acceptance |

只有指定Reviewer/User/Core可以關閉其review/approval；POC self-test不等於external ACK。

## Internal milestones

| Milestone | State | Summary |
| --- | --- | --- |
| M0 | `COMPLETE` | readiness execution/review complete |
| M1 | `COMPLETE` | frozen candidates/contract harness signed off |
| M2 | `COMPLETE` | Core closed Gate 1；Gemma normal finalist；Qwen P7.1 FAIL且依defect waiver保留Gate 2A資格 |
| M3 | `COMPLETE` | 雙candidate final-surface Pi evidence獲User review；Gemma唯一model finalist；Core external ACK pending |
| M4 | `IN_PROGRESS` | attempt 001～005永久保留；r5把Accepted Audio controller closure納入entry，並以單session全鏈diagnostic阻擋未收斂runner進入attempt 006 |

## Cumulative P1～P12 rule

- Gate 1 accepted evidence：P1/P6/P7/P10A/P11/P12。
- Gate 2A immutable evidence：Gemma P2/P8 FAIL、P3/P4/P5 PASS；Qwen P2/P8 FAIL、P3/P5 PASS、
  P4需Core threshold decision。User以語意分離完成model selection，不改寫machine results。
- Gate 2B accepted evidence：P9/P10B。
- Execution commit為ancestor且execution-surface lock、runtime/model/config/protocol/fixture、
  Pi/environment及manifest identity相同時不重跑；evidence/docs commit不造成失效。
- Drift只使affected item失效；gate transition本身不構成rerun理由。
- P5只在Pi的2A執行；P9/P10B只用Accepted Audio正式kit，surrogate無credit。

詳細方法見[Execution Plan](m4b_execution_plan.md)與[Traceability](m4b_traceability_crosswalk.md)。

## Open dependencies and risks

- **Qwen disposition**：P7.1 rebuild READY `18152.025 ms`維持`FAIL / SLOW_RECOVERY`；Gate 2A
  P2 0/30且P4未達TTFT target。User已排除Qwen正式Gate 2B，不得把waiver或machine result改寫為PASS。
- **Core closure ACK**：`DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001`已接受四份replacement
  receipts、User Qwen defect waiver、兩名Gate 2A candidates並關閉Gate 1。
- **Gate 2A Pi observations**：final exact `e2b59fac…`完成Qwen `004`及Gemma `002`；兩次均
  clean/read-only/offline/`swap=0`、零full-model rehash、log hygiene PASS且cleanup零殘留。
- **P1 startup**：Gemma 1024與Qwen 512皆通過initial READY；capacity必須綁exact artifact，禁止恢復
  implicit 4096 default或把144-token protocol envelope當Engine capacity。
- **P1.2 true-cold startup**：Qwen在兩次reboot-separated、零full-model-hash診斷中約`19.2 s`
  READY，其中約`19.0 s`位於native `Engine()`。原因尚未歸因；User已defer後續matrix。Gate 2A
  僅可用Qwen 30秒操作觀察窗口繼續P2/P3/P4/P5/P8，P1仍為10秒且不得新增P credit。
- **P6**：native cancel已知可能nondeterministic；只有P7完整PASS才允許Conditional escalation。
- **P4**：Gemma TTFT P95 `727.983 ms`、decode P50 `11.293 tok/s`為PASS；Qwen未達TTFT target且
  保留`Core threshold decision required`，但已不進正式Gate 2B。
- **P5**：固定continuous 512-token chunks共用單一outer timer；chunk完成固定CONTINUE，禁止
  early RESULT及結果後adaptive fixture。
- **Gate 2 R4 review**：source findings已關閉；Gate 2A final evidence亦獲User review。這只完成
  M3 selection，不使failed Gemma integration自動符合Gate 2B consumer。
- **Gate 2B r5 execution closure**：LLM input/output/Engine/pre-warm與marker行為保持r4不變；新增
  Accepted Audio `controller-r2` manifest `6bb24f9a…76f4`、wheel inventory、isolated venv及import
  origin驗證。正式attempt 006前，必須先由同一exact SHA通過static preflight及一次真正
  VAD→ASR→LLM→TTS/ALSA、resource/log/cleanup全鏈diagnostic；兩種模式都不建立evidence或P credit。
- **Gate 2B runner containment與PSI裁決**：Accepted Audio child一律從run-owned temporary cwd啟動，
  任何cwd-relative runtime side effect隨該目錄刪除，不得污染exact Git checkout。User於2026-08-29
  指示從prospective Gate 2B execution surface完全移除system-wide memory PSI採集與gate；P9仍嚴格檢查
  system-used、`swap=0`、OOM、leak、temperature、throttling、ownership與cleanup。`DELIVERY-023`請Core
  接受此契約調整；ACK可在已授權執行期間補入，final delivery前仍須連結。
- **P2/P3/P8 semantics adjustment**：User已裁決P2為完整candidate configuration的整合
  qualification、P3為deterministic safety boundary、P8只判history/KV isolation。`DELIVERY-019`
  已請Core確認；final evidence已獲User核准，Gemma以model finalist身分入選。Core ACK仍待補，
  現有receipt不得改寫，新的integration revision不得覆蓋本輪觀察。
- **Gate 2B integration entry**：Gemma current product pairing P2 3/30，永久不得直接作combined
  baseline。Replacement `litert-lm-v0.16.0-pi-g2b-r1`與model-finalist receipt只含Gemma並採held-out
  20-session first contact。Initial formal `G2B-PI-COMBINED-001`在VAD/ASR啟動後由Accepted TTS
  verifier拒絕不完整受控store；兩個sherpa wheel source未staging，LLM未啟動、session為零且cleanup
  零殘留，故為`INCONCLUSIVE`而非candidate FAIL。其sanitized evidence SHA-256為
  `50714d383cbefb75b96ae320e86bbb1ca64756f897f6b05eddd64f4f61a008f0`。Replacement lock
  `c671e2…45d74`已在任何residency前驗證完整TTS input closure。Attempt 002確實啟動四個domain，
  但第一筆resource sample發現Pi kernel雖有`CONFIG_PSI=y`，卻以`CONFIG_PSI_DEFAULT_DISABLED=y`
  且未帶`psi=1`啟動；session仍為零，四domain均cooperative stop且零ALSA/process residue，故仍為
  `INCONCLUSIVE`。其evidence SHA-256為`1e3604406ce71d6a05a44bd3781838d92d6643ded4a67e32e7147db075f5f8ce`。
  歷史attempt 003～005亦不得覆寫；其User review/發布狀態與正式P disposition分開保存。Current
  r5 lock加入`controller-r2` closure、安全Audio-domain診斷及恰一session的
  `--diagnostic-session-only`。它先用獨立`--preflight-only`驗證全部static entry、model receipt
  metadata與thermal/OOM/memory probes，再以相同四domain/ALSA/controller執行單session；兩者
  通過才可執行`G2B-PI-COMBINED-006`。Current r14不再要求PSI probe或`psi=1`；Attempt 001～005不得覆寫。
  Independent review可後補。Core對
  `DELIVERY-019/021`的ACK依User裁決
  可於執行期間補入，但final delivery前必須收到。
- **Accepted Audio**：Audio annotated tag `audio_m4`（tag object `24b2571a…`）指向accepted completion
  `5694ead4…`與Core acceptance `RESP-AUDIO-M4-GATE2B-001` / `be19b70b…`已確認。20-WAV
  deterministic lock `d7d308…e0f8`與delivered manifest `1b3356…30a2`已完成repo-external靜態
  provenance audit；replacement runner會在residency計時前驗證全部Audio artifact/runtime identity。
  User已授權Pi path inventory、staging與execution；Accepted controller `controller-r2`亦成為runner
  的manifest-locked execution input。既有Audio-only PASS與單session diagnostic都不提供M4B P9/P10B credit。
- **Evidence safety**：不commit model、wheel、native binary、raw output、prompt/payload、credential或endpoint。
- **Post-delivery informational backlog**：正式POC交付完成後，才續作P1.2 cold-start cause matrix，
  並視成本對未入選candidate執行no-credit Gate 2B同包比較；不得延誤或改寫正式單一finalist流程。

## Active packets

- [Gate 1 cumulative packet](../../poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md)
- [Gate 1 P6.1/P7.1 corrective packet](../../poc_llm/tests/gate1/GATE1-P6.1-P7.1-REDESIGN-001.md)
- [P1.2 cold READY supplemental packet](../../poc_llm/tests/gate1/P1.2-PI-COLD-READY-ATTRIBUTION-PACKET-001.md)
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
- [P1.2 cold READY assessment](../response/ASSESSMENT-LLM-M3-P1.2-COLD-READY-DIAGNOSTIC-001.md)
- [Qwen Gate 2A preflight assessment](../response/ASSESSMENT-LLM-M3-GATE2A-QWEN-PREFLIGHT-001.md)
- [Gate 2A final User review](../response/ASSESSMENT-LLM-M3-GATE2A-20260829-USER-REVIEW.md)
- [Gate 1 closure delivery draft](../delivery/DELIVERY-018-PM-LLM-POC-GATE1-CLOSURE.md)
- [Gate 2A closure and Gemma finalist delivery](../delivery/DELIVERY-021-PM-LLM-POC-GATE2A-CLOSURE-GEMMA-FINALIST.md)

## Governing and historical inputs

2026-08-29 round-close audit：`docs/pm_handoff/`四份直屬Income仍具治理效力。M4b contract與
Core task boundary控制最終交付；cumulative R3 ACK控制跨gate累積與carry-forward；Gate 1 closure
ACK繼續驗證carried evidence。Gate 2 Pi authorization已完成其M3用途並原文移入history。

- [M4b contract](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [Pi packet R2 ACK (historical)](../pm_handoff/history/RESP-LLM-POC-PI-EXECUTION-PACKETS-002.md)
- [Cumulative Gate R3 ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001.md)
- [Gate 1 closure ACK](../pm_handoff/DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md)
- [Gate 2A Pi authorization (historical)](../pm_handoff/history/ACK-LLM-POC-M3-GATE2-PI-AUTH.md)
- [Gate 2A exact-SHA Core authorization (historical)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE2A-PI-AUTH-001.md)
- [ARM64-to-Pi transition ACK (historical)](../pm_handoff/history/ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [Pi entry point](../../poc_llm/README.md)
