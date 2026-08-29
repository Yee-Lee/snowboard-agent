# LLM M4：Gate 2B Cumulative Audio + LLM Final Validation

狀態：`IN_PROGRESS`

Entry authority：`USER AUTHORIZED COMMIT/PUSH + PI STAGING/EXECUTION / REVIEW MAY FOLLOW`

## Goal

以Accepted Audio POC full SHA/kit及2A provisional candidate，在一次4GB combined run完成P9與
P10B，連結Gate 1/2A accepted evidence後提出final winner/no-go。

## Entry

- Accepted Gate 1 cumulative receipt與Gate 2A User-reviewed model-finalist decision；Gemma identity固定。
- Gemma current Gate 2A integration configuration的P2 FAIL不得直接作Gate 2B baseline；先建立新的
  versioned integration candidate、事前凍結並以precommitted/held-out cases完成entry qualification。
- Core ACK `DELIVERY-019`及Gate 2A closure/model-finalist delivery；依User裁決可於Gate 2B執行
  期間補入，但final delivery前必須收到，不得因此改寫既有machine result。
- Core-recorded Accepted Audio handoff ID、full SHA、executable kit與known limits。
- `G2B-PI-COMBINED-001/002`及其`INCONCLUSIVE`證據不可覆寫；修正版以
  `G2B-PI-COMBINED-003`執行。Independent executable review可依User裁決後補，Core result ACK
  必須在final delivery前收到。
- Pi 5 4GB、`swap=0`、offline、clean exact SHA；combined process ownership固定。

2026-08-28已確認Accepted Audio source entry：delivery `POC-audio-DEL-2026-001-R1`、annotated
tag `audio_m4`（tag-object SHA `24b2571a23dde2f77027242b61142b0c1a59924c`）指向accepted completion SHA
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`、corrected delivery
SHA `ca51bce9b4e205d9c9faf004d41c27169f108a3f`、Core response
`RESP-AUDIO-M4-GATE2B-001` / `be19b70b1dd91674e7ff981eb9d6b2dca9741f54`。Source identity
dependency已解除；combined runner、manifest/schema已在worktree完成，Pi artifact staging與
Pi execution authorization仍未完成。

2026-08-28 worktree已補`run_gate2b_pi_v1.py`、artifact-independent coordinator、continuous
process-tree sampler、Accepted Audio/Gate 2A entry schemas、result schema及closed lock。它把真實
ASR transcript只在記憶體送入LLM，再把LLM `speak`文字只在記憶體送入TTS；不使用deterministic
reasoner或P9 surrogate。Initial replacement Gate 2 suite 49/49；R2 review關閉獨立證據、leak gate與runtime
canary scan，但重現partial startup時owner root尚未保存，使stop failure無法fallback
cleanup。R3 review已關閉這個partial-start finding；attempt-before-await、逐一root capture、
partial-allocation fallback與runner proof保留均成立。Shared Gate 2B scored request的broken/reset
pipe現已轉為typed candidate FAIL並完成fault matrix。R4 reviewer已重現59/59 Gate 2與
136/136 Gate 1，關閉R3-F2並授權exact milestone commit/push。Gate 2A model-finalist receipt已完成，
User亦已授權Pi；Audio artifact staging仍是後續execution entry，因此尚未產生P9/P10B credit。
原development-ready consumer只接受全PASS Gate 2A receipt。User已選定Gemma model finalist，
但final machine receipt保留P2/P8 FAIL，因此不能偽造舊schema receipt。Worktree replacement已建立
`litert-lm-v0.16.0-pi-g2b-r1`、只含Gemma的model-finalist receipt/consumer、generic held-out-first
prompt、完整Audio input authentication與post-READY typed failure。Attempt 002 lock為
`c671e2438833c6bc26dec32ca5f49909e325d25d8e134ef3fcb0b996da845d74`；current revision另加入
不建立evidence、不載入domain的`--preflight-only` smoke，lock
`da1a8a58adc86d412b960f3ee3107e5040ca75a0efe9a13570bb70271f84cb90`。User於2026-08-29
明確授權完成後直接commit/push並進入Pi staging/execution，independent review可後補；因此M4已改為
`IN_PROGRESS`。Pi pure preflight重現network namespace繼承host sysfs的已知假陽性，正式packet已補
private mount與read-only sysfs；該診斷未建立evidence、未載入模型。

Initial formal attempt `G2B-PI-COMBINED-001`（execution SHA `2dd7d28270afe15d2b31ab8c4ee5c3c98b694cd5`）
已建立immutable evidence，但Accepted TTS verifier在LLM/residency完成前發現controlled store漏放兩個
sherpa wheel source。VAD/ASR已啟動、TTS拒絕啟動、LLM未啟動、session為零，reverse cleanup為零
殘留，因此P9/P10B均為`Blocked`、整體`INCONCLUSIVE`，不是candidate failure。Sanitized evidence
SHA-256為`50714d383cbefb75b96ae320e86bbb1ca64756f897f6b05eddd64f4f61a008f0`。Replacement在任何domain
residency前驗證兩個wheel identity，使用新execution SHA、input/evidence root與run ID
`G2B-PI-COMBINED-002`。

Attempt 002完整驗證Audio closure並啟動VAD/ASR/TTS/LLM，但第一筆residency sample發現Pi的
`/proc/pressure/memory`不存在。Kernel具有`CONFIG_PSI=y`但預設停用，boot亦未指定`psi=1`；因此
沒有合法的P9 full-PSI counter。零session執行，四domain均cooperative stop且零process/ALSA
residue，整體仍為`INCONCLUSIVE`。Sanitized evidence SHA-256為
`1e3604406ce71d6a05a44bd3781838d92d6643ded4a67e32e7147db075f5f8ce`。Attempt 003以可逆`psi=1`
測試開機提供必要counter。它必須先以獨立smoke驗證source/lock、Audio/Core/controlled inputs、
Gate 2A chain、runtime wheel、model receipt metadata、offline/swap/ALSA與memory/PSI/OOM/thermal；
smoke不建立evidence、不消耗formal run ID且零residency。實際P9/P10B仍須其後有效evidence才能判定。

Attempt 003（execution SHA `26e654968bbd4c9b2a9a2796d21cfbc01fba7446`）已進入第一筆combined
session，但LLM在parent/child同為15秒的deadline邊界失去typed terminal，P10B為immutable `FAIL`。
後續no-credit cold/warm歸因確認：同一298-token prefill在reboot後首個post-READY request需16.704秒，
same-boot fresh process/Engine為5.061秒；完整cold output另有schema-invalid及marker缺失。User已授權
corrective pairing `r3`與重做實驗：128 tokens對rendered prompt硬性執行、speak-only constrained JSON與
current-marker pattern、
固定non-sensitive pre-warm完成後才發布`INFERENCE_READY`，以及15秒child deadline外2秒terminal-only
observer grace。`DELIVERY-022`要求Core把pre-warm納入正式child lifecycle；ACK可後至但final交付前須連結。
Attempt 003不覆寫，corrective result在User review前仍不得發布。

## Work

- P9/P10B共用一次Audio+LLM load與20 sessions，不建立額外residency-only重複run。
- P9記錄system-used、完整process-tree PSS/RSS、CPU、threads/owners、PSI、temperature與cleanup；
  capacity gate只用`MemTotal-MemAvailable<=3584MiB`，sum RSS僅diagnostic。
- P10B執行20個ASR fixture→LLM→TTS sessions（5s cadence），驗證Audio semantics、LLM schema、
  latency、thermal、history/stale result、log hygiene與final residue。
- 只對combined integration實際改變的boundary做predeclared focused regression；不例行重跑1/2A。

## Exit

P9與P10B PASS；Gate 1 P1/P6/P7/P10A/P11/P12、2A P2/P3/P4/P5/P8及2B P9/P10B manifest
chain完整。Reviewer/Internal Tester/User關閉finding後交Core final winner/no-go。POC狀態在Core final
ACK前只可為`Ready for internal review`。

## Prohibited

不得用surrogate取得P9/P10B credit、用8GB補救4GB failure、因gate transition broad-rerun、提交
raw prompt/output/weights/credential，或在Accepted Audio dependency缺失時啟動combined test。
