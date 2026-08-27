# LLM M3：Gate 2A Remaining LLM-only Pi Validation

狀態：`REDESIGNED / NOT_STARTED`

## Goal

消費Gate 1 cumulative receipt，只在Pi完成尚未驗證的P2、P3、P4、P5、P8，與Gate 1的
P1/P6.1/P7.1/P10A/P11/P12合併形成完整2A decision。Gemma為normal finalist；Qwen以User
defect waiver保留candidate資格且P7.1維持FAIL。2A最多提出一名provisional finalist。

## Entry

- Gate 1至少一名normal finalist、User-waived Qwen candidate及accepted cumulative receipt/evidence manifest。
- Gate 1 execution commit為current clean checkout的ancestor；execution-surface lock、shared
  component、Pi與environment identity未漂移。Evidence/docs commit不要求Git SHA equality。
- `G2A-PI-LLM-002` executable revision、Reviewer/User/Core review與Pi authorization就緒。

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
