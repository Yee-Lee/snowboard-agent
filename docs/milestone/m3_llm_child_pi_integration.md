# LLM M3：Gate 2A Remaining LLM-only Pi Validation

狀態：`NOT_STARTED`

## Goal

消費Gate 1 cumulative receipt，只在Pi完成尚未驗證的P2、P3、P4、P5、P8，與Gate 1的
P1/P6.1/P7.1/P10A/P11/P12合併形成完整2A decision。Gemma為normal finalist；Qwen以User
defect waiver保留candidate資格且P7.1維持FAIL。2A最多提出一名provisional finalist。

## Entry

- Gate 1至少一名normal finalist、User-waived Qwen candidate及accepted cumulative receipt/evidence manifest。
- Gate 1 execution commit為current clean checkout的ancestor；execution-surface lock、shared
  component、Pi與environment identity未漂移。Evidence/docs commit不要求Git SHA equality。
- `G2A-PI-LLM-002` executable revision、Reviewer/User/Core review與Pi authorization就緒。

2026-08-27 entry audit發現舊`001` executable無法執行accepted `002` scope。2026-08-28已在
worktree建立`run_gate2a_pi_v2.py`、`gate2a-pi-lock-v2.json`、cumulative entry/result schemas、
candidate-specific P5 adapter/config、64-output product profile與P8 fixture；initial replacement Gate 2
suite 49/49、Gate 1 regression 136/136。2026-08-28 R2 targeted review關閉F1/F5，但重現P5
completion/timeout transition race，且no/late terminal等scored protocol failure未經實際runner
產生凍結的FAIL語意。R3已將completion/cancel決策納入單一lock，但review重現
native cancel實際呼叫仍可在conversation close後發生，且scored broken pipe/shutdown
timeout與mixed-stage precedence仍可產生錯誤`INCONCLUSIVE`。R3-F1/F2現已用Condition lifetime、
post-call marker、窄scored exception matrix與primary-before-rebuild裁決修正；59項Gate 2測試包含
完整protocol integration。R4 reviewer已重現59/59 Gate 2、136/136 Gate 1與十輪定向競態/裁決
實驗，關閉R3-F1/F2並授權exact milestone commit/push；Pi仍未授權，未產生Pi credit。完整追蹤見
`docs/response/ASSESSMENT-LLM-M3-GATE2A-ENTRY-AUDIT-001.md`。
本次commit只凍結development-ready source；只有取得pushed exact SHA、Pi授權與完成重建staging
後，index才可把M3改為`IN_PROGRESS`。

## Work

- P2/P3：10 valid model cases×3；10 invalid normalizer fixtures×3；100% exact schema/fallback/log hygiene。
- P4：cold 3、warmup 3、hot 20；raw/P50/P95；miss negotiable target交Core裁決。
- P5：Pi-only continuous 512-token chunks共用單一15秒outer timer；15–17秒TIMEOUT、same-child
  health、standard rebuild；fast chunk固定CONTINUE，不接受workstation result。
- P8：5個nonce/trap single-turn、no prior-state/KV accumulation、hash-only evidence。
- Link Gate 1 receipt；ordinary startup/cleanup不重新計為P1/P7。

## Exit

P2/P3/P5/P8 PASS，P4方法完整且PASS或有written threshold decision。Qwen若被提名為provisional，
必須明載P7.1 FAIL及User/Core written workaround disposition，不得把waiver轉為PASS。
Reviewer/Internal Tester/User review完成後才提交provisional proposal；Core只可發provisional ACK，
不是final winner。

## Prohibited

不得例行重跑Gate 1 P items、暗中rehash/repair drift artifact、在workstation跑P5、改post-result
fixture/threshold、或把2A稱為final baseline。
