# M4B-MVA：產品等價量測

狀態：`IN_PROGRESS / WORKSTATION CONTRACT AND RUNNER PREPARATION`

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

Entry review結論：本機contract/schema/runner準備已獲範圍；commit、push、Pi存取／重開機／執行、
benchmark發布與candidate/profile建議仍各自需要User核准。因此milestone進入workstation
`IN_PROGRESS`，hardware work維持`Blocked — authorization not yet requested`。

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

1. 完成WP01 controller、sanitized evidence writer、non-recursive surface lock及其workstation verification。
2. execution snapshot需User核准commit/push；尚未請求。
3. Pi目前關機；WP02/WP03的存取、6次reboot與執行尚未請求授權。
4. Accepted Audio MVA parity及physical audible-onset方法尚未確認；未解除前只規劃LLM subsystem claim。
5. 12個private held-out sessions的評估者、operator與受控呈現方式待執行前指定。
6. 所有benchmark結果與profile建議在User審核前不得發布。

## Prohibited

不得修改Income、Core product repo或composition root；不得提交model/wheel/native binary、raw output、
private prompt/audio、credential或endpoint；不得沿用舊single-turn/full-envelope數字冒稱產品等價；不得
在未授權時存取Pi、reboot、安裝、傳輸artifact、切換網路、commit、push或發布結果。
