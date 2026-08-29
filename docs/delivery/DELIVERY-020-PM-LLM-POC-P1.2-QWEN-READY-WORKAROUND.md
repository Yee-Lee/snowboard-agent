# DELIVERY-020 — P1.2 Qwen Cold READY Record and Gate 2A Continuation

- Date: 2026-08-29
- From: LLM POC Team
- To: PM / Core Designer
- Status: `REQUESTED — ACK MAY FOLLOW EXECUTION`
- Branch: `llm`
- Exact replacement commit: provided after commit/push; never prefilled

## Decision and continuation notice

The User directed the LLM POC Team to preserve the Qwen true-cold READY finding as supplemental P1.2,
defer further cause-isolation, and continue the already-authorized remaining Gate 2A work with a
Qwen-only 30-second operational READY observation window. Core ACK may follow execution. This does not
change the formal P1 10-second contract, produce P1/P1.2 credit, or authorize Gate 2B.

## Preserved finding

The first frozen Qwen Gate 2A observation stopped before READY at 10 seconds and remains immutable
`INCONCLUSIVE`. Two reboot-separated diagnostics, with zero full model hashes, observed READY at about
19.2 seconds. Stage attribution placed about 19.0 seconds inside native `Engine()` construction. The
diagnostics then completed READY identity, PING, SHUTDOWN and process cleanup successfully. P1.2 records
this result for later cold-boot integration work without claiming a cache, storage or capacity cause.

## Replacement execution boundary

- Gemma retains the 10-second operational READY window.
- Qwen may be observed for at most 30 seconds while executing only P2/P3/P4/P5/P8.
- Every result records contract `10000 ms`, operational `30000 ms`, workaround
  `P1.2_COLD_READY_OBSERVATION`, and `gate_credit=FORBIDDEN`.
- Model/runtime/config/receipt, Engine capacity, prompt, fixtures, P thresholds and repetitions remain
  unchanged; no model is rehashed or retuned.
- `G2A-PI-QWEN-001` is preserved. Continuation requires a new boot, run ID, exact replacement SHA,
  execution-surface digest and evidence directory.
- Benchmark publication, semantic adjudication and provisional proposal remain blocked on User review.

## Core ACK requested

Please acknowledge P1.2 as a deferred supplemental experiment and accept the 30-second value strictly
as a Qwen operational observation workaround for completing the current Gate 2A comparison. Any later
change to the formal P1 contract or production startup policy remains a separate Core decision.
