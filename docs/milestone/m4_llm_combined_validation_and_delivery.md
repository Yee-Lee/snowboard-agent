# LLM M4：Gate 2B Cumulative Audio + LLM Final Validation

狀態：`NOT_STARTED`

## Goal

以Accepted Audio POC full SHA/kit及2A provisional candidate，在一次4GB combined run完成P9與
P10B，連結Gate 1/2A accepted evidence後提出final winner/no-go。

## Entry

- Accepted Gate 1 cumulative receipt與Gate 2A receipt；provisional candidate identity固定。
- Core-recorded Accepted Audio handoff ID、full SHA、executable kit與known limits。
- `G2B-PI-COMBINED-001` executable revision及Reviewer/User/Core review完成。
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
136/136 Gate 1，關閉R3-F2並授權exact milestone commit/push。Gate 2A receipt、Pi授權與
Audio artifact staging仍是後續的execution entry，因此尚未產生P9/P10B credit。
本次commit只凍結development-ready source；Gate 2A receipt、Pi授權與Audio/LLM staging未齊備前，
M4保持`NOT_STARTED`。

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
