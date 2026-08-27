# ASSESSMENT-LLM-M2-GATE1-CUMULATIVE-20260827-USER-REVIEW

- **Status**: `SUPERSEDED BEFORE PUBLICATION / P6.1 AND P7.1 PENDING`
- **Gate**: Gate 1 cumulative P1/P6/P7/P10A/P11/P12
- **Proposed gate result**: `WITHDRAWN — NO CURRENT GATE VERDICT`
- **Proposed finalists**: `WITHDRAWN — P6.1/P7.1 REQUIRED`
- **Core closure review**: `NOT YET REQUESTED`

## 1. Proposed final decision

> **Supersession notice:** Official LiteRT-LM v0.16 source review proved that the legacy P6 used
> synchronous `send_message()` with an API documented for asynchronous inference, and that its P7
> immediately inherited the cancellation-conditioned process. The table below is retained review
> history, not a publishable verdict. `GATE1-P6.1-P7.1-REDESIGN-001` must replace both P items before
> Gate 1 can be adjudicated.

| Candidate | P1 | P6 | P7 | P10A | P11 | P12 | Gate 1 candidate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gemma 4 E2B | PASS | Conditional escalation | PASS | PASS | PASS | PASS | PASS |
| Qwen2.5 1.5B Q8 | PASS | Conditional escalation | FAIL | PASS | PASS | PASS | FAIL |

Gate 1 has one eligible candidate and therefore closes `PASS` if the User approves this cumulative
adjudication. Qwen has now been fully evaluated; it is not left `Blocked`, deferred or unexplained.
No further Qwen retry, token retuning or timeout change is proposed.

## 2. Gemma accepted evidence proposed

- Formal run: `G1-PI-COMPAT-007-20260827T131517Z-002`.
- Execution SHA: `97a20dceac2fd762987f3e64f331b84e933e03e5`.
- Execution surface: `739fb3649bc08e501bd3c8935cb8c9d02faf5b5f8b4522b269a59337b983c28b`.
- Sanitized result: `d765874af319299e481d09357690da4c6c18a85775745b363627bc01e0b384ce`.
- Custody manifest: `f222b4ba64af269c23de8a0d6191798f3edf63667cbcbe40816c7ac56daf093d`.
- READY `837.103 ms`; P10A `20/20`; wall p50/p95 `2363.372 / 3229.589 ms`.
- PSS slope `0.236386 MiB/session`; system-used slope `-0.587393 MiB/session`;
  maximum temperature `51.0°C`; all throttling samples `0x0`.
- P6 had no correlated terminal within 500 ms and is valid `Conditional escalation`. P7 proved
  TERM/wait/group absence, rebuild READY `478.670 ms`, recovery RESULT, fatal mapping and cleanup.

## 3. Qwen cumulative evidence proposed

### 3.1 Isolated normal lifecycle and stability

- Run: `G1-PI-COMPAT-007-QWEN-ISOLATED-20260827T134110Z`.
- Execution SHA: `3baf0536b2e787e9ba5a5610d165c0d6b6b0c83e`.
- Execution surface: `e3fe10b4d29ded97417ec76ea0d8b5388da4603d87fb09c2093f2bfae087e18f`.
- Sanitized wrapper result:
  `b40bc521805e98a191247e30117b3514277f654bd8a64b8f43ff16056766a0eb`.
- Custody manifest:
  `0e434432d8d0e3ec73885420087acd1ff6838e15b4b18765dab6b2e720c139e9`.
- Boot isolation: uptime `42.210 s`, no pre-existing adapter and no prior candidate workload.
- Qwen 512 READY `3490.826 ms`; P1 PASS; P10A `20/20`; P11/P12 PASS.
- Wall p50/p95 `7060.710 / 7759.658 ms`; PSS slope `0.027154 MiB/session`;
  system-used slope `-0.331529 MiB/session`; maximum temperature `52.7°C`; throttling `0x0`.
- The later redundant pre-P6 Engine startup timed out. That v7 runner-sequencing outcome is not
  used as Qwen P6/P7 credit; it motivated the prospectively frozen focused packet below.

### 3.2 Focused cancel, force-abort and rebuild

- Run: `G1-QWEN-P6P7-ISOLATED-20260827T135911Z`.
- Execution SHA: `b9a91cabd9e357ef81232d907aafd2a7a5c60200`.
- Execution surface: `a0e4d4a06d0df6285f9b37d212d68cd3bf9cd367107c18d7e9a7637b2dbe226f`.
- Sanitized result:
  `3660b3f496f91f11389d099323f0691e12ae979e563f75827a1d40a75849055c`.
- Custody manifest:
  `9cf6de8db58c12b793dd7b64e50b4c4e80f5c3b54ca67926a57503271f69943e`.
- Boot isolation: uptime `75.450 s`, no pre-existing adapter and no prior candidate workload.
- Healthy prerequisite READY `3479.672 ms`; active generation observed.
- P6: no terminal in `500.631 ms`, valid `Conditional escalation` pending P7.
- P7: force-abort path proceeded to the only required rebuild; rebuild emitted no READY within the
  unchanged ten-second bound. P7 is therefore `FAIL`, making the conditional P6 insufficient for
  finalist eligibility.

## 4. Runner finding and future impact

The evidence rejects the broad claim that Qwen cannot meet initial READY because it follows Gemma.
Qwen initial READY passes in a clean isolated run. The v7 runner nonetheless contains unnecessary
Engine churn between P10A and P6, and Qwen's contract blocker is the required post-abort rebuild
READY. Detailed lessons and Gate 2/product implications are recorded in
`ASSESSMENT-LLM-M2-GATE1-RUNNER-EXECUTION-LESSONS-001`.

No runner redesign may reinterpret Qwen P7 as PASS. Gate 2A should carry only Gemma and must avoid
introducing unrelated Engine rebuilds between remaining work packages.

## 5. Core status

Incoming `DELIVERY-LLM-POC-M4B-CUMULATIVE-GATES-R3-ACK-001` accepts the cumulative gate design,
v7 authentication/receipt/timeout logic and R3 target `4dc76d1…`. It authorizes execution but says
Gate 1 closure and final P credit require formal evidence-manifest review.

Per User direction, no intermediate experiment or SHA will be sent to Core. After User approval,
one Gate 1 closure delivery will map the accepted R3 design to the later additive execution fixes,
all three accepted evidence surfaces and the sole Gemma finalist proposal.

## 6. Pi cleanup

- Both custody manifests verify every retained file.
- `/tmp` artifact bind removed; persistent model/wheel modes restored to `0664`.
- zram restored as 2 GiB priority 100; NetworkManager active; `throttled=0x0`.
- Pi checkout is clean; no LLM adapter or runner process remains.
- Direct-IP monitoring proved restoration even while mDNS resolution remained unavailable.

## 7. User decision requested

Approve or reject these statements together:

1. Accept the Gemma formal evidence and the two Qwen isolated receipts above.
2. Accept Qwen cumulative P1/P10A/P11/P12 PASS, P6 Conditional escalation and P7 FAIL.
3. Accept Gate 1 aggregate PASS with Gemma as the sole finalist.
4. Authorize commit/push of the sanitized assessment, runner lessons, milestone/index updates and
   one Gate 1 closure delivery for Core review.
