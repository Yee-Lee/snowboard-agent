# LLM M4：Gate 2B Cumulative Audio + LLM Final Validation

狀態：`REDESIGNED / BLOCKED ON ACCEPTED AUDIO`

## Goal

以Accepted Audio POC full SHA/kit及2A provisional candidate，在一次4GB combined run完成P9與
P10B，連結Gate 1/2A accepted evidence後提出final winner/no-go。

## Entry

- Accepted Gate 1 cumulative receipt與Gate 2A receipt；provisional candidate identity固定。
- Core-recorded Accepted Audio handoff ID、full SHA、executable kit與known limits。
- `G2B-PI-COMBINED-001` executable revision及Reviewer/User/Core review完成。
- Pi 5 4GB、`swap=0`、offline、clean exact SHA；combined process ownership固定。

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
