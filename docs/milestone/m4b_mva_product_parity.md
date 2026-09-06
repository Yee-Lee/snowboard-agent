# M4B-MVA：產品等價量測

狀態：`IN_PROGRESS / STEP 5 DELIVERED / CORE STEP 6 ACK PENDING`

External gate：`M4B-MVA-POC OPEN`

Baseline：`M4B-MVA-001`

Core profile candidate：`core-m4b-mva-001`（非production lock）

## Goal

完成Core七步流程Step 5：以Gemma 4 E2B mobile、LiteRT-LM 0.16.0及Pi 5 4GB建立產品等價
MVA量測，回答same-session Conversation reuse、compact `text/end`、可選pre-warm、穩態記憶體、
受控replacement、短句語意品質與可繼承性能範圍。結果只供Designer在Step 6採用；不改寫既有
Gate 2A/2B machine結果，也不等於Core Gate 3或M4B Accepted。

本工作推進的新交付檢查項為：`M4B-MVA-POC`須取得一份identity完整、產品等價、可重現且經
User發布前審核的committed result packet，供Core Designer採用profile並明確解除gate。

## Authority and entry review

- Income：`REQUEST-LLM-POC-M4B-MVA-MEASURE-001`；target SHA-256
  `5afb24e8ec7ad67853745ec290672c6b48a174819928936609556fefd184a2c2`。
- Core frozen source：commit `034a50f260e7434e586dddf64ef500da3b1b2b4e`。
- Core delivery receipt：commit `492f022c06962eb93b37fa0e93765f43690be1b2`；Step 4完成，Step 5開始。
- User於2026-09-05確認已交付，要求POC依新產品設計修正量測surface；Pi需要時另行申請。
- 既有M4已完成且保持immutable；本工作不新增model selection、不重標P8/P9/P10B，亦不修改
  product composition root、Reasoner產品政策或Accepted Audio實作。

Entry review結論：本機contract/schema/runner準備已獲範圍；原始workstation階段時，
commit、push、Pi存取／重開機／執行、benchmark發布與candidate/profile建議仍各自需要User核准。

2026-09-06 User接續指示「同意。直接做到要連接pi之前」：授權本機依賴恢復與完成WP01，
並涵蓋供Pi取得的execution snapshot commit/push；Pi連接、reboot、執行及benchmark/profile
發布仍未授權。此指示取代前段對本機commit/push的pending狀態。

2026-09-06 User後續確認Pi已可連線，並明確指示開始Pi測試。Core offline
execution Income指定exact SHA `ac25aa104adcadb3b6274ca6f9c3d4154b4004ee`與surface
`f774c8d018445b91bef4fa3b59bcc4f288d6699deb1fd09a2cb9baf8f2ddc461`。LLM operator已完成
SSH、乾淨checkout、surface、private config、resource stop gate與NetworkManager回復能力確認；
Pi execution/reboot現已授權，benchmark/profile發布仍需User審核。

## Product-parity surface

| Surface | POC design |
| --- | --- |
| Runtime/model | frozen Gemma 4 E2B mobile + LiteRT-LM API 0.16.0；exact artifact identity沿用R3 provenance |
| Semantic output | constrained JSON exact keys `text/end`；`end=false`須nonblank text，`end=true`須empty text |
| Session lifecycle | child READY時無Conversation；每個product session建立一個Conversation；正常turn重用；end/cancel/dirty state close |
| Product facts | `name=雪板`、`role=你的語音小助理`、`locale=zh-TW`、perceptions=`listen`、actions=`speak/rest` |
| Reasoner boundary | model只提供回答與end intent；POC oracle驗證Reasoner應組成speak/listen或rest，不讓model產生canonical action envelope |
| Prompt/token | tracked exact system/user template bytes；32 user-new、128 output、1024 KV只作本次受控measurement envelope |
| Pre-warm |唯一A/B變因為disposable public inference `none/once`；完成後丟棄Conversation，product session另開 |
| Resource policy | 不用8-attempt或48 MiB trigger；自然60 sessions與三次受控recovery分開；MemAvailable安全線512 MiB |
| Claims | 無exact Accepted Audio與audible-onset proof時只報`llm_subsystem`，不得以TTFT/TTC代替M4 E2E |

## Work packages

### MVA-WP01 — contract and snapshot

- 建立MVA專用prompt、semantic/wire/result schema、profile、公開catalog與validation oracle。
- workstation tests涵蓋same-session reuse、cross-session close、dirty-state discard、strict `text/end`、
  user-new admission、no old full-envelope keys及sanitized result shape。
- execution前產生surface lock，固定case order、repetitions、commands、timeouts、raw sanitized paths與
  exact commit SHA。只有committed/pushed clean SHA可申請Pi。

Exit：contract tests通過；surface manifest無遞迴hash；Reviewer/User可核對exact SHA。

### MVA-WP02 — runtime API proof and A/B timing

- 在selected Pi/runtime實證Conversation reuse下的render、exact tokenizer、token count、response
  constraints、close、cancel與dirty-session語意。
- cold固定`N1/O1/N2/O2/N3/O3`，共6次獨立reboot；same-boot replacement固定
  `N1/O1/.../N5/O5`，共10次fresh process/Engine。
- 每筆保存READY、open、first-turn TTFT/TTC、caller TTC、second-turn TTC、close與各token分項。

Exit：全部預定樣本或明確Invalid/Blocked/Fail均以同一schema保留；不做小樣本P95推論。

### MVA-WP03 — memory and recovery

- selected baseline執行3個fresh-child cycle，每cycle 20個雙輪session；不在8/16主動recycle。
- session 11–20固定為steady window；逐cycle報owner PSS與system-used slope、median delta及完整trajectory。
- READY_NO_SESSION下以`capacity_test`做3次受控same-key replacement，驗single-flight、owner exit、
  trust identity及barrier；不以recycle loop掩蓋Audio/system占用。

Exit：60 sessions與3次recovery完整，或依frozen stop rule保留Incomplete/Fail；cleanup證據完整。

### MVA-WP04 — manual semantics and Audio scope

- 評估者在freeze後保管12個未供調參sessions；每例一次generation，逐項人工rubric。
- POC只提交case ID、operator、rubric、overall與sanitized reason，不提交raw prompt/answer/audio。
- 若Accepted Audio exact package與同timebase speech-end→meaningful audible-onset方法可用，另量M4 E2E；
  否則audible latency為`null`且scope固定`llm_subsystem`。

Exit：12例均有Pass/Fail/Unclear；Unclear不算Pass；Audio缺口不被估算或TTFT取代。

### MVA-WP05 — review and delivery

- Technical Lead先審identity/environment/packet、artifact/fixture hash、exit/cleanup，再審品質與效能。
- benchmark結果與profile建議先交User review；User核准後才發布committed packet與正式delivery。
- Core Designer Step 6決定token/capacity/prewarm/watchdog/目標採用並明確解除gate。

Exit：Designer ACK記錄result full SHA、accepted scope、profile digest及`gate released`。

## Result semantics and stop conditions

- Machine sample：`PASS`、`FAIL`、`INCONCLUSIVE`、`Blocked`；target miss另保留target、observed、
  bottleneck與adjustment，不自動淘汰model或宣告全計畫no-go。
- 每startup 120秒、每generation 30秒、每mode 1800秒、每memory cycle 7200秒。
- `MemAvailable < 512 MiB`、swap增加、OOM/kernel fault、`get_throttled != 0x0`、溫度`>=80°C`、
  identity drift、sampler failure或cleanup無法證明時停止受影響run/cycle並保存結果。
- Packet發出後不得改case、順序、surface、門檻或有效樣本；需改產品語意／比較面時回Core發新版baseline。

## Current open items

2026-09-05本段完成：Income/intake identity、MVA profile、exact prompt/template、semantic/session/wire/
machine/manual schemas、public catalog、lifecycle/Reasoner/token/resource oracle及LiteRT session backend已建立。
MVA targeted tests 25/25 PASS；POC全測試245 PASS並保留一筆既有Gate 1 thread-warning。這些是
workstation contract evidence，不是runtime API proof、Pi result或benchmark。
工作站更換所需的完整續接資訊、檔案inventory、測試命令、round-close audit與所有open items見
[`HANDOFF-LLM-M4B-MVA-WORKSTATION-001`](../response/HANDOFF-LLM-M4B-MVA-WORKSTATION-001.md)。

1. WP01 final source為`7bb332670b5fdf45f05f07dd385bec94d914b4e1`、surface
   `61764d0737fcf374468621bd90d4765739d2f9b2b06e4314b1dbb73229f74e89`；MVA本機67/67 PASS，Pi
   exact surface驗證PASS。
2. `MVA-001-api-proof`因operator誤用pretty receipt file SHA而在model load前成為INCONCLUSIVE；一筆
   `IDENTITY_DRIFT`證據完整保留，不覆寫。修正為canonical receipt digest與獨立`MVA-002` ledger。
3. 正式離線`MVA-002`已完成全部23個machine case：六個不同boot cold、十個same-boot replacement、
   三個20-session memory cycle及三個recovery。Technical audit驗證23筆ledger、單一identity、1,822筆
   schema-valid samples、summary/checkpoint binding及cleanup；audit SHA-256為`6708ca21…65487`。
   Runner/audit回傳PASS，User完成數值與語意審閱後將LLM-only machine hardware disposition定為`PASS`。
4. 本輪無Accepted Audio exact package與同timebase physical audible-onset方法；結果固定
   `audible_onset_ms=null / NO_AUDIO_PROOF / scope=llm_subsystem`。這不是未執行的LLM machine case；
   User明確批示暫不執行，未取得新的User核准前不得啟動；若後續獲准，Core組合Accepted M4a Audio
   時才量speech-end到first meaningful audible output。
5. 12個private held-out sessions已由operator在Pi一次執行，User逐例審閱；12 sessions、24 generations、
   零retry、cleanup PASS。Git僅保存schema-valid sanitized rubric，不含raw prompt/answer/audio。
6. 私有machine review artifact SHA-256為`b7614ae1…9df05`、mode `0600`；User已完成benchmark
   publication review。這不等於production profile selection或Core gate release。
7. User已審閱並指示在報告向Core保留時間拆解：cold/once首輪caller TTC `7.704 s`
   中約`3.305 s`為Conversation open、`1.689 s`為generation-to-first-token、`2.708 s`
   為後續25 tokens完成，非「首token後又decode六秒」。Core Step 6必須評估提前建立乾淨
   Conversation、簡化stream-safe semantic frame、分批送TTS及同timebase audible-onset量測；
   現有MVA-002保持append-only，新設計須另建Core baseline後才可宣稱產品等價。
8. Memory review顯示global owner-PSS peak `1981.592 MiB`出現在once-prewarm replacement；
   no-prewarm 60-session cycles peak `1800.639 MiB`。三個steady windows的owner late-minus-early
   分別為`+0.125 / +0.063 / +11.406 MiB`，system-used則為`+1.391 / 0 / -2.000 MiB`；
   第三輪`+11.406 MiB`是前後各五筆median差，不是端點淨增加；session 11→20實際只
   `+0.422 MiB`，中間16–19暫時形成較高resident plateau後回落。未見跨cycle一致的system
   leak，但未具allocator-level attribution，且prewarm約`0.2 GiB`額外resident ownership仍需
   Core在保留warmed Conversation方案中繼續驗證。Audio未合併，不得將LLM-only headroom
   當作完整產品capacity結論。
9. User review結論為目前未見session count造成progressive memory pressure；不建議固定session數
   recycle。Core應在Audio composition後訂owner-PSS upper bound、MemAvailable reserve及
   swap/OOM/thermal/dirty-cleanup gates，並以連續超界與hysteresis排除短暫plateau；exact threshold
   由Step 6決定，不由POC從LLM-only envelope臆定。
10. User已接受API/session lifecycle、token/context capacity、recovery/cleanup、system
    resource/thermal envelope與evidence identity/audit。三輪各20 sessions皆逐次重開
    KV `0 → 174 → 233`後close，
    session 20未累積前19個session的KV；memory soak量的是Engine/process retention，不是20-turn
    context-capacity。
11. User直接要求補足long-session coverage；append-only `MVA-LONG-002`完成三個fresh-child cycle，
    每輪單一Conversation皆完成17 turns並於attempted turn 18得到typed `CONTEXT_LIMIT`。KV由turn 1
    的167增至turn 17的910；固定128 output reserve使`910 + 128 > 1024`，所以還未計下一筆input即
    正確拒絕。三輪fresh recovery皆由KV 0開始並PASS，cleanup owner absent；live long context約增加
    73.1 MiB owner PSS。此補測不回填或改寫MVA-002，Core須據此設計context/output budgeting與
    summarization/truncation或controlled rollover。
12. H01–H12 User-reviewed結果為8 Pass / 4 Fail / 0 Unclear。H03 missed end、H05 knowledge fact、
    H06 over-refusal、H11 brevity保留為真實Fail；User接受四項皆為非阻擋後續優化。Core須加強
    prompt/response budget與general knowledge，並由controller提供idle Conversation reset fallback。

2026-09-06新工作站續接：確認`llm`位於交接SHA
`7a56137b7b2d65219ea4ff2065ab2773c179a0af`且起始worktree clean，建立ignored local context。
新增`poc_llm/harness/mva_surface.py`，以explicit inventory產生non-recursive source manifest；
驗證完整inventory、exact bytes、trusted digest並拒絕missing input、越界與symlink。
最初六項standard-library測試PASS，`git diff --check`通過；隨後完成controller/writer，
擴充完整inventory並產生execution lock，最終MVA targeted為53項PASS。
新機Python 3.14.6最初缺`jsonschema`，既有MVA測試在import階段停止；User隨後授權安裝並
直接完成Pi連接前準備。隔離`.venv`已恢復，controller、worker、receipt驗證、resource probes、
durable evidence writer與surface manifest已完成；本輪最終驗證與平台差異詳見
[`HANDOFF-LLM-M4B-MVA-PI-ENTRY-001`](../response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md)。
此為workstation self-test，沒有產生benchmark；Pi executable-path proof與private 23-case rehearsal見
[`ASSESSMENT-LLM-M4B-MVA-PI-ENTRY-001`](../response/ASSESSMENT-LLM-M4B-MVA-PI-ENTRY-001.md)，MVA gate仍Open。

## Prohibited

不得修改Income、Core product repo或composition root；不得提交model/wheel/native binary、raw output、
private prompt/audio、credential或endpoint；不得沿用舊single-turn/full-envelope數字冒稱產品等價；不得
在未授權時存取Pi、reboot、安裝、傳輸artifact、切換網路、修改canonical權限、
commit、push或發布結果。本輪Pi execution/reboot、兩個artifact group-read修正、正式離線執行、
長Conversation補測、人工評估與結果發布均已獲User授權／審閱；push未包含在本輪commit授權內。
