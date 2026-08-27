# LLM M2：Gate 1 Cumulative Stability and Core Integration

狀態：`USER COMPLETE / CORE GATE-COMPLETION REVIEW`

## Goal and delivery contribution

對Gemma 4 E2B與Qwen2.5 1.5B在產品Pi 5 4GB上正式完成P1、P6、P7、P10A、P11、P12，
回答LLM穩定性與Core persistent-child整合可行性，最多保留兩名Gate 1 finalists。這些P evidence
在identity不變時直接供2A/2B cumulative decision使用，不因gate transition重跑。

## Entry

- Gate 0與M1完成；兩名candidate/runtime/model/config/license identity固定。
- Product target為Pi 5 4GB、Debian 13 aarch64、`swap=0`、offline、`throttled=0x0`。
- Runtime wheel與兩個模型已在Pi持久artifact root，正式執行前仍須read-only staging與clean exact SHA。
- Reviewer已核准cumulative design，Core已ACK R3 execution entry，User已授權Pi執行與後續
  append-only source SHA。Gate 1結果仍須User核准後才可commit/publish或送Core closure。

## Historical `006`

Run `G1-PI-COMPAT-006-20260826T125959Z-001`與manifest
`34cb51b0bdb04a042281722db37514bce1daba234391fa79570482faa53d2208`永久保留。
其valid environment與cleanup證據成立，但READY 10秒包含完整模型SHA；因此定性為packet defect，
不是candidate incompatibility，不產生zero-finalist或P credit。

## Replacement work packet

Authoritative packet為`poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md`；source lock為
`poc_llm/harness/gate1-pi-compat-lock-v7.json`。核心設計：

- model各自只做一次streaming SHA，且在READY clock前完成；read-only receipt供後續child使用；
- v2 wheel installer只做一次content authentication；
- normal lifecycle同時完成P1與P10A的20 sessions，不另跑重複stability loop；
- fault lifecycle同時完成P6 observation與P7 force-abort；一次rebuild完成recovery proof；
- P11/P12使用packet-level pre/post evidence，不在每個child重複。

## Exit

- 每個candidate有P1/P6/P7/P10A/P11/P12有效狀態、raw manifest、cleanup與review record。
- Eligibility：P1/P7/P10A/P11/P12 PASS，P6 PASS或由P7支持的`Conditional escalation`。
- Technical Lead、Internal Tester、Reviewer與User完成result review；Core以manifest SHA接受cumulative
  boundary與最多兩名finalists。
- Gate 2A只執行P2/P3/P4/P5/P8；不得重跑identity未變的Gate 1 P evidence。

## Withdrawn legacy aggregate

| Candidate | P1 | P6.1 | P7.1 | P10A | P11 | P12 | Gate 1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gemma 4 E2B | PASS | PASS | PASS | PASS | PASS | PASS | PASS / finalist |
| Qwen2.5 1.5B Q8 | PASS | PASS | FAIL | PASS | PASS | PASS | FAIL / User waiver to Gate 2A |

Gemma formal receipt is `G1-PI-COMPAT-007-20260827T131517Z-002`. Qwen's reboot-isolated normal
lifecycle is `G1-PI-COMPAT-007-QWEN-ISOLATED-20260827T134110Z`; its prospectively frozen focused
P6/P7 receipt is `G1-QWEN-P6P7-ISOLATED-20260827T135911Z`. Detailed hashes, metrics, cleanup and
adjudication are in `ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-20260827-USER-REVIEW.md`.

The former Gemma-only aggregate was withdrawn before publication. Independent reboot-isolated
P6.1/P7.1 now replace both legacy credits. Qwen P7.1 independently recovered READY in `18152.025 ms`,
so its score remains FAIL. The User retains Qwen for Gate 2A by explicit defect waiver and bounded
workaround opportunity; Gemma remains the normal finalist. Core completion review is pending.

## Retry and prohibitions

Valid mandatory FAIL不retune、不same-revision rerun；reviewed infrastructure/evidence
INCONCLUSIVE最多一次identical rerun。不得補Qwen 0.5B、在workstation跑P5、提交model/raw output/
prompt/payload/credential。P6.1/P7.1設計、source、schema與tests須先由User審核，之後才可開始Pi run。
