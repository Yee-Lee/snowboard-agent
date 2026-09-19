# LLM POC Milestone and Contract Gate Index

本檔是External Gate、internal milestone、目前授權與風險的唯一狀態入口。

最後更新：2026-09-19

2026-09-19 closure／intake補記：Core已於2026-09-16接受M4B same-bytes Pi product verification；
Accepted commit `f87cfa50b9c9415430973076a59c6b1961228090`已push至`origin/core`。因此舊
`M4B-MVA-POC`與`M4B-MVA-EFFICIENCY`不再是active blocker，其POC deliveries已被Core產品baseline
採用並納入M4B completion。Core於commit `56962d5c9802c1355d21187def74769c29f02620`
交付byte-identical `M4C-SS` request；User於2026-09-19授權workstation開發、限定Pi preflight及本輪
commit/push。Formal execution、network切換、reboot以外的target mutation與result publication仍未授權。

以下Pi storage與MVA內容是已完成M4B round的歷史紀錄，不構成M4C-SS授權。Core已接受Phase 3搬遷；Pi的clean canonical checkout、指定data roots、
product `8279e79`、artifact identity與private evidence transfer/legacy-run cleanup均有receipt。
2026-09-06只讀驗收再次確認SHA、workspace、config、current binding、零product symlink與
零writable product file。Core已授權exact-SHA離線MVA；User於2026-09-06確認Pi可連線並指示
開始Pi測試。LLM operator已確認SSH、乾淨checkout、frozen surface、private config、
resource stop gates與離線one-shot回復能力。User授權後已修正model/wheel的group-read；private
replacement source已修正venv import root、model suffix presentation、native constrained-schema subset、
evidence identity及shutdown邊界，並在Pi完成全部23個machine case rehearsal。replacement
commit/surface的exact-SHA `MVA-002`已正式完成23/23 machine cases；User亦完成benchmark、長對話
補測與H01–H12審閱。permanent purge仍需獨立User授權，Audio整合測試由User批示暫不執行。
Core其後於`f6e0c742f6e32fdc0e16915c6e59f42e5dd6cd69`交付`M4B-MVA-EFFICIENCY-002`；
source/destination byte comparison PASS，Income SHA-256為`e13b7175…92c4`。新gate已Open；User要求
POC把constraint不支援後的停止點擴大為bounded solution discovery，並授權Pi-native
development/test/debug後回workstation完成規劃、commit及push。Pi-native開發方式是repository
general rule，不需逐任務例外。新增fallback進formal comparison前仍需Core revision；
dirty Pi development run不取得正式credit。

## Current reachability

狀態：`LLM POC COMPLETE / M4B CORE ACCEPTED / M4C-SS IN_PROGRESS / PI PREFLIGHT PARTIAL / EXECUTION NOT AUTHORIZED`。

目前唯一active LLM POC delivery是M4C true streaming-speak feasibility。它以Accepted M4B與M4A為
read-only inputs，先完成intake、deterministic controller、evidence/acoustic scaffold及execution freeze；
只有獲得新的User授權後才可存取Pi或執行prototype。POC結果不關閉`M4C-SS`，Core Designer仍是gate owner。

原LLM POC M0～M4與Gate 1/2A/2B保持完成且結果immutable。Core於2026-09-05正式交付
`M4B-MVA-001`產品等價量測，User確認由既有POC團隊進入七步流程Step 5；本機先修正為
same-session Conversation reuse、compact `text/end`及evidence-backed prewarm/resource設計。
2026-09-06 User先授權恢復本機測試環境並完成連接Pi前的準備，後續
確認Pi可連線並指示開始Pi測試。Pi 5、Debian 13、CPython 3.13.5、乾淨
checkout及入場resource gates已實測確認；hardware execution與User benchmark review均已完成。
DELIVERY-025已在`23fb481007ebaf9d4c58d66b762a65aacec9196c`提交並由Core接收。Core未直接
解除原gate，而是以`M4B-MVA-002`新增dependent efficiency experiment。User已要求保留D/H風險
量測並擴大P fallback responsibility；POC先做exact API/source discovery，並保留既有結果immutable。

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
| Gate 2A | `CLOSED / CORE ACK` | P2, P3, P4, P5, P8 | final evidence已review；Gemma唯一model finalist；machine P2/P8 FAIL不改寫 |
| Gate 2B | `CLOSED / CORE FINAL WINNER ACK` | P9, P10B | Attempt 006完成20/20；machine P9/P10B FAIL不改寫；Core接受User known-runtime-defect waiver與Gemma winner |
| Gate 3 | `OUT_OF_POC_SCOPE` | Core tests | Core production acceptance |
| M4B-MVA-POC | `CLOSED / INCORPORATED INTO CORE M4B ACCEPTANCE` | MVA-002 result；no legacy P credit | Core adopted the POC inputs and User accepted M4B at `f87cfa5…` |
| M4B-MVA-EFFICIENCY | `CLOSED / INCORPORATED INTO CORE M4B ACCEPTANCE` | J/S2、conditional H、listen-only Reasoner及V2D2 | Delivery 003/004 became M4B design inputs；no separate formal rerun remains |
| M4C-SS | `OPEN / PI PREFLIGHT PARTIAL` | engineering preflight only | timing/identity completion → frozen execution → User publication review → Core decision |

只有指定Reviewer/User/Core可以關閉其review/approval；POC self-test不等於external ACK。

## Internal milestones

| Milestone | State | Summary |
| --- | --- | --- |
| M0 | `COMPLETE` | readiness execution/review complete |
| M1 | `COMPLETE` | frozen candidates/contract harness signed off |
| M2 | `COMPLETE` | Core closed Gate 1；Gemma normal finalist；Qwen P7.1 FAIL且依defect waiver保留Gate 2A資格 |
| M3 | `COMPLETE / CORE ACK` | 雙candidate final-surface Pi evidence獲User review；Gemma唯一model finalist；Core final ACK整併接受019/021語意與選型 |
| M4 | `COMPLETE / CORE FINAL WINNER ACK` | Attempt 006完成20/20 combined sessions；Core接受User waiver、Gemma POC winner與R3 manifest |
| M4B-MVA | `COMPLETE / CORE INCORPORATED` | MVA、efficiency及V2D2交付已成為Accepted M4B input；歷史結果保持immutable |
| M4C-SS | `IN_PROGRESS / PI PREFLIGHT PARTIAL` | 48/48 targeted tests；model identity與I2S speaker＋USB mic duplex PASS；`<=50 ms`未證明 |

## Cumulative P1～P12 rule

- Gate 1 accepted evidence：P1/P6/P7/P10A/P11/P12。
- Gate 2A immutable evidence：Gemma P2/P8 FAIL、P3/P4/P5 PASS；Qwen P2/P8 FAIL、P3/P5 PASS、
  P4需Core threshold decision。User以語意分離完成model selection，不改寫machine results。
- Gate 2B immutable evidence：P9/P10B machine FAIL；User defect waiver不改寫分數，Gemma仍為POC winner。
- Execution commit為ancestor且execution-surface lock、runtime/model/config/protocol/fixture、
  Pi/environment及manifest identity相同時不重跑；evidence/docs commit不造成失效。
- Drift只使affected item失效；gate transition本身不構成rerun理由。
- P5只在Pi的2A執行；P9/P10B只用Accepted Audio正式kit，surrogate無credit。

詳細方法見[Execution Plan](m4b_execution_plan.md)與[Traceability](m4b_traceability_crosswalk.md)。

## Open dependencies and risks

- **M4C-SS authority**：User授權workstation開發與測試至pre-Pi gate。Pi access、prototype execution、network、
  reboot、artifact change/download、commit、push及benchmark/candidate publication仍須各自適用的明確授權。
- **M4C-SS target/acoustic identity**：Pi/model identity及I2S speaker＋獨立USB microphone duplex已做
  engineering preflight；USB capture實際為48 kHz mono S16_LE。`<=50 ms` uncertainty、runtime/TTS/Audio、
  clean checkout、private roots及offline identity仍未完整驗證，缺一不得開始formal measurement。
- **M4C-SS bounded design**：只比較`B1-IMMEDIATE-SEQUENTIAL`與
  `B2-ONE-LOOKAHEAD-COALESCE`，共82個fixed samples/subcases；禁止第三candidate、open-ended tuning或
  修改M4A/Core public contract。詳見[M4C-SS milestone](m4c_streaming_speak.md)。

- **Pi storage migration**：Phase 1～3已完成並獲Core接受；2026-09-06 read-only postcheck再次確認
  canonical checkout、product/artifact identity、private evidence root與零product symlink/writable file。
  它不再阻擋MVA。permanent purge仍需獨立User授權，本輪efficiency工作不要求purge。
- **Execution snapshot**：Core原授權exact SHA
  `ac25aa104adcadb3b6274ca6f9c3d4154b4004ee`與surface `f774c8d0…c461`；Pi目前位於
  exact SHA且保持乾淨。首次offline prepare-install的artifact group-read已依User授權修正；後續
  runtime/layout/API缺口已在獨立private candidate修正並完成23/23 Pi machine rehearsal。舊SHA不被
  靜默修改；replacement exact SHA `7bb332670b5fdf45f05f07dd385bec94d914b4e1`、surface
  `61764d07…74e89`的正式`MVA-002`已完成23/23 machine cases。User審閱後machine disposition為`PASS`。
- **Workstation migration / WP01**：新checkout已核對交接SHA `7a56137b…`並建立ignored local
  context；隔離測試環境、controller、sanitized writer與surface lock已完成。MVA targeted tests
  通過；完整suite的macOS/Linux/x86與canonical-path限制已在原交接SHA對照重現，並未宣告全綠。
  詳見[Pi entry handoff](../response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md)。
- **M4B-MVA Step 5**：Core frozen source `034a50f260e7434e586dddf64ef500da3b1b2b4e`、delivery
  receipt `492f022c06962eb93b37fa0e93765f43690be1b2`與Income SHA-256 `5afb24e8…2c2`已核對。
  Workstation/Pi執行、User benchmark review及DELIVERY-025 commit `23fb481…`均已完成；原結果保持immutable。
- **M4B-MVA-EFFICIENCY**：Core source `f6e0c742f6e32fdc0e16915c6e59f42e5dd6cd69`、
  Income SHA-256 `e13b7175…92c4`及destination baseline `23fb481…`已核對。User要求POC在P path
  不支援時繼續尋找solution；WP00先核對native regex/grammar、incremental constrained J、compact
  constrained JSON與last-resort diagnostic。新增formal candidate須先經User review及Core revision；
  implementation前先commit/push本規劃；Pi-native development/test/debug其後依general rule執行，
  完成後回workstation建立implementation commit/push。本輪兩階段commit/push均獲授權。formal target
  result仍須clean pushed implementation SHA、frozen packet及append-only evidence，結果發布另行授權。
- **MVA parity delta**：舊fresh-per-operation/full-envelope/mandatory-prewarm surface只作provenance；
  新量測必須使用same-session Conversation reuse、exact `text/end`、Reasoner-owned action policy、
  no/once prewarm A/B及獨立natural-soak/recovery。舊Gate結果不得混入主要樣本或改標。
- **MVA Audio scope**：本輪無exact Accepted Audio package與同timebase
  speech-end→meaningful audible-onset，僅交付`llm_subsystem / null / NO_AUDIO_PROOF`。User已批示
  暫不執行Audio整合測試，新的User核准前不得啟動；M4 E2E維持Open但不阻擋LLM Step 5 delivery。
- **MVA manual quality**：12個freeze後private held-out sessions已在Pi一次執行並由User審閱；
  sanitized結果8 Pass / 4 Fail / 0 Unclear。H03/H05/H06/H11保留Fail並接受為非阻擋後續優化；
  raw prompt/answer/audio保持private且不進Git。

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
  已由Core final ACK確認；final evidence獲User核准，Gemma以model finalist身分入選。現有receipt
  不得改寫，新的integration revision不得覆蓋本輪觀察。
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
  Independent review可後補。Core final ACK已整併接受`DELIVERY-019/021/022/023`並接受
  `DELIVERY-024`的winner與waiver；production acceptance仍由Core Gate 3另行判定。
- **Gate 2B final result**：exact SHA `0c75536…`的preflight與單session diagnostic均PASS；formal
  `G2B-PI-COMBINED-006`完成20/20真實VAD→ASR→LLM→TTS/ALSA sessions，schema、marker、trap、history、
  offline、thermal與cleanup全部符合。Frozen verifier因combined PSS slope `5.900893 MiB/session`及
  late-early median `131.578 MiB`回傳P9/P10B FAIL；system-used slope僅`0.101957 MiB/session`、peak
  `2382.969 MiB`，swap/OOM/throttle為零。User將此分類為LiteRT-LM Engine/Session resident-retention
  known defect、保留machine FAIL並grant waiver，選定Gemma為POC winner。`DELIVERY-024`與R3 winner
  manifest已獲Core final-winner ACK；Core承接Gate 3 mitigation與exact-product-SHA複驗。
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

- [M4C-SS milestone](m4c_streaming_speak.md)
- [M4C-SS intake and preparation boundary](../response/ACK-LLM-POC-M4C-STREAMING-SPEAK-001.md)

Completed M4B references：

- [M4B-MVA product-parity milestone](m4b_mva_product_parity.md)
- [M4B-MVA efficiency experiment plan](m4b_mva_efficiency.md)
- [M4B-MVA efficiency intake and arrangement](../response/ACK-LLM-POC-M4B-MVA-EFFICIENCY-002.md)
- [M4B-MVA efficiency scope-expansion assessment](../response/ASSESSMENT-LLM-M4B-MVA-EFFICIENCY-SCOPE-EXPANSION-001.md)
- [M4B-MVA workstation snapshot and Pi entry handoff](../response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md)
- [M4B-MVA intake and design mapping](../response/ACK-LLM-POC-M4B-MVA-MEASURE-001.md)

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
- [Gate 2B User-approved winner assessment](../response/ASSESSMENT-LLM-M4-GATE2B-20260829-USER-REVIEW.md)
- [Gate 2B closure and Gemma winner delivery](../delivery/DELIVERY-024-PM-LLM-POC-GATE2B-CLOSURE-GEMMA-WINNER.md)
- [POC winner manifest R3](../../poc_llm/deliveries/POC-llm-DEL-2026-001-R3.md)
- [Core Gate 2B final-winner ACK](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001.md)

## Governing and historical inputs

2026-09-19 intake audit：`M4C-SS` request是唯一active direct Income。M4B contract、task boundary、
Gate 1 ACK、MVA measurement及efficiency request都已被Core M4B Accepted disposition納入或完成，
目前仍因本輪尚未round-close commit而保留原路徑；下一次獲授權的round-closing commit必須保持內容
不變移入`docs/pm_handoff/history/`並同步更新Document Index。歷史MVA/Gate結果保持immutable。

- [M4C-SS request](../pm_handoff/REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001.md)
- [M4b contract (retained governing Accepted-M4B provenance)](../pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md)
- [M4B-MVA measurement request (retained immutable surface input)](../pm_handoff/REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md)
- [M4B-MVA efficiency request (retained Accepted-M4B provenance)](../pm_handoff/REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002.md)
- [Pi storage-curation request (completed history)](../pm_handoff/history/REQUEST-POC-LLM-PI-STORAGE-CURATION-001.md)
- [M4B-MVA offline execution request (completed history)](../pm_handoff/history/REQUEST-POC-LLM-M4B-MVA-OFFLINE-EXECUTION-001.md)
- [Pi packet R2 ACK (historical)](../pm_handoff/history/RESP-LLM-POC-PI-EXECUTION-PACKETS-002.md)
- [Cumulative Gate R3 ACK (historical)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001.md)
- [Gate 1 closure ACK (retained immutable Gate 2A provenance)](../pm_handoff/DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001.md)
- [Gate 2A closure ACK (historical)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE2A-CLOSURE-ACK-001.md)
- [Gate 2B final review (historical)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE2B-FINAL-REVIEW-001.md)
- [Gate 2B final-winner ACK (historical)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001.md)
- [Gate 2A Pi authorization (historical)](../pm_handoff/history/ACK-LLM-POC-M3-GATE2-PI-AUTH.md)
- [Gate 2A exact-SHA Core authorization (historical)](../pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE2A-PI-AUTH-001.md)
- [ARM64-to-Pi transition ACK (historical)](../pm_handoff/history/ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001.md)
- [LLM POC workflow](../llm_poc_workflow.md)
- [Document index](../DOCUMENT_INDEX.md)
- [Pi entry point](../../poc_llm/README.md)
