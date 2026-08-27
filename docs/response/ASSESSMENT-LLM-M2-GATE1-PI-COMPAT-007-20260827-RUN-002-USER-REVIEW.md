# ASSESSMENT-LLM-M2-GATE1-PI-COMPAT-007-20260827-RUN-002-USER-REVIEW

- **Status**: `AWAITING USER REVIEW / NOT PUBLISHED`
- **Packet**: `G1-PI-COMPAT-007`
- **Formal run**: `G1-PI-COMPAT-007-20260827T131517Z-002`
- **Execution SHA**: `97a20dceac2fd762987f3e64f331b84e933e03e5`
- **Execution surface SHA-256**: `739fb3649bc08e501bd3c8935cb8c9d02faf5b5f8b4522b269a59337b983c28b`
- **Sanitized result SHA-256**: `d765874af319299e481d09357690da4c6c18a85775745b363627bc01e0b384ce`
- **Custody manifest SHA-256**: `f222b4ba64af269c23de8a0d6191798f3edf63667cbcbe40816c7ac56daf093d`
- **Core acceptance**: `PENDING`

## Review conclusion

The formal Gate 1 aggregate result is `PASS` with one provisional finalist:
`CAND-LRT-G4E2B-MOBILE-R1`. This assessment is an internal User review artifact; no benchmark or
candidate result may be published or relayed to Core before User approval.

| Candidate | P1 | P6 | P7 | P10A | P11 | P12 | Candidate result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CAND-LRT-G4E2B-MOBILE-R1` | PASS | Conditional escalation | PASS | PASS | PASS | PASS | PASS |
| `CAND-LRT-Q25-15B-Q8-R1` | FAIL | Blocked | Blocked | Blocked | PASS | Blocked | FAIL |

## Gemma evidence

- Explicit Engine capacity: `1024`, bound to exact model SHA
  `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`.
- READY: `837.103 ms`; PING/PONG, shutdown, exit `0`, wait and process-group absence all passed.
- Stability: `20/20` RESULT sessions; wall p50/p95 `2363.372 / 3229.589 ms`.
- PSS slope: `0.236386 MiB/session`; system-used slope: `-0.587393 MiB/session`.
- Late/early median deltas: PSS `8.688 MiB`; system-used `-26.516 MiB`.
- Maximum recorded temperature: `51.0°C`; every sample and final probe reported
  `throttled=0x0`.
- Native CANCEL did not emit a correlated terminal within 500 ms and is therefore
  `Conditional escalation`. Level-2 TERM/wait left no process group; rebuild READY was
  `478.670 ms`, recovery returned RESULT and clean shutdown passed. This satisfies the frozen P7
  support rule without rewriting P6 as PASS.

## Qwen evidence

- Explicit Engine capacity: `512`, bound to exact model SHA
  `faa60663b333290c1496c499828b21d3e3254a788cacd8cce917ce0f761a2dc9`.
- Model authentication and P11 identity checks passed.
- The child did not emit READY within the frozen `10,000 ms` deadline. The runner recorded
  `P1=FAIL`, sent TERM, waited successfully and proved the process group absent.
- P6/P7/P10A/P12 remain `Blocked`; no credit is inferred from the earlier non-scoring P1.1 run.

## Infrastructure rerun disposition

Run `G1-PI-COMPAT-007-20260827T130624Z-001` front-loaded both model authentications before the
Gemma workload. Its later Qwen READY observation was classified as infrastructure-inconclusive
because receipt cache conditioning was no longer comparable. Revision `97a20dc…` interleaved each
candidate's one-pass authentication with its immediate launch and added mandatory cleanup on READY
failure. The packet-authorized single infrastructure rerun reproduced Qwen's READY timeout, so no
further retry or retuning is allowed. Run 001 remains preserved and is not overwritten.

## Environment, custody and cleanup

- Raspberry Pi 5 4GB, Debian 13 aarch64, clean exact checkout.
- Pre/post: `swap=0`, all non-loopback interfaces down, routes offline, no sensitive environment
  names and `throttled=0x0`.
- Custody manifest verifies every stored file. Raw stderr/receipts remain outside Git and no prompt,
  payload, model output, model, wheel, credential or endpoint is proposed for commit.
- After operator cleanup: Wi-Fi and zram restored, model/wheel permissions restored, no LLM child or
  runner process remains and `throttled=0x0`.

## User decision requested

Approve or reject all three statements together:

1. Accept run `...T131517Z-002` as the formal Gate 1 evidence set.
2. Accept Gate 1 aggregate `PASS` with Gemma as the sole provisional finalist.
3. Authorize publication of the sanitized result summary and the subsequent Core handoff, while
   retaining `CORE ACCEPTANCE PENDING` until Core ACKs the manifest and cumulative boundary.
