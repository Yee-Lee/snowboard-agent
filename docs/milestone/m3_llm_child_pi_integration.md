# LLM M3：Gate 2A Remaining LLM-only Pi Validation

狀態：`COMPLETE / CORE ACK`

## Goal

消費Gate 1 cumulative receipt，只在Pi完成尚未驗證的P2、P3、P4、P5、P8，與Gate 1的
P1/P6.1/P7.1/P10A/P11/P12合併形成完整2A decision。Gemma為normal finalist；Qwen以User
defect waiver保留candidate資格且P7.1維持FAIL。2A最多提出一名provisional finalist。依User核准的
P2/P3/P8語意分離，M3可完成模型選型，但P2失敗的tested integration configuration不得被稱為
product baseline或直接進入Gate 2B scoring。

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
實驗，關閉R3-F1/F2並授權exact milestone commit/push。Core其後以
`ACK-LLM-POC-M3-GATE2-PI-AUTH`授權exact `ed7aaca2e187b2287d442d6841e1ab2610b67570`
進行staging與Gate 2A；User於2026-08-29確認Pi可連線並要求繼續，因此M3進入`IN_PROGRESS`，
但尚未產生Pi credit。完整追蹤見
`docs/response/ASSESSMENT-LLM-M3-GATE2A-ENTRY-AUDIT-001.md`。
上述commit是原R4/Core授權surface。P1.2 replacement另以User授權的新clean exact SHA執行，
該SHA在commit/push後交付Core；本輪重建並驗證clean/offline/read-only staging，再按不可變packet
執行。任何未在replacement lock中聲明的surface drift皆停止並回報，不在Pi修補。

首次Qwen Gate 2A observation在10秒前未READY，保留為`INCONCLUSIVE`。兩次獨立重開機診斷
均在約19.2秒READY，且約19.0秒位於native `Engine()`；未證明cache、storage或capacity因果。
User將後續cause matrix記為deferred P1.2，並授權replacement surface以Qwen-only 30秒操作窗口
繼續remaining work。它不修改P1 10秒契約、不產生P1/P1.2 credit。Core ACK可後至雙candidate
execution與User review；它仍是external Gate closure及Gate 2B新revision entry所需的書面紀錄。

`G2A-PI-QWEN-002`其後在零model access時因host sysfs mount仍顯示`wlan0=up`而preflight
`INCONCLUSIVE`；network namespace實際route為零。Replacement packet以private mount namespace
重新掛載read-only sysfs，且在environment preflight前取得evidence directory ownership。No-model
probe已通過；正式retry必須使用新boot、`QWEN-003`、新evidence root及新exact SHA。

## Work

- P2/P3：10 valid model cases×3；10 invalid normalizer fixtures×3；100% exact schema/fallback/log hygiene。
- P4：cold 3、warmup 3、hot 20；raw/P50/P95；miss negotiable target交Core裁決。
- P5：Pi-only continuous 512-token chunks共用單一15秒outer timer；15–17秒TIMEOUT、same-child
  health、standard rebuild；fast chunk固定CONTINUE，不接受workstation result。
- P8：5個nonce/trap single-turn、no prior-state/KV accumulation、hash-only evidence。
- Link Gate 1 receipt；ordinary startup/cleanup不重新計為P1/P7。

## Exit

2026-08-29 final surface `e2b59fac609e0d768ff3554754363900cbed70a9`完成兩名candidate的
reboot-isolated Pi execution。Qwen machine disposition為P2 FAIL、P3 PASS、P4
`Core threshold decision required`、P5 PASS、P8 FAIL；Gemma為P2 FAIL、P3/P4/P5 PASS、P8 FAIL。
兩者P8皆為`DEPENDENCY_LIMITED_BY_P2`，沒有觀察到prior-state leakage，stored receipt不改寫。

User已審核完整sanitized evidence並選定Gemma為唯一**model finalist**、排除Qwen正式Gate 2B、
關閉M3/Gate 2A POC execution與selection round。Gemma current prompt/config仍因P2 FAIL而不是
deliverable product baseline；Gate 2B scoring前必須建立、事前凍結及review新的integration-qualified
candidate revision，不得用調整後重跑覆蓋本輪證據。完整裁決見
`docs/response/ASSESSMENT-LLM-M3-GATE2A-20260829-USER-REVIEW.md`。Core final-winner ACK已整併接受
`DELIVERY-019`語意分離與`DELIVERY-021`唯一Gemma model-finalist selection；machine結果不改寫。

## Prohibited

不得例行重跑Gate 1 P items、暗中rehash/repair drift artifact、在workstation跑P5、改post-result
fixture/threshold、或把2A稱為final baseline。
