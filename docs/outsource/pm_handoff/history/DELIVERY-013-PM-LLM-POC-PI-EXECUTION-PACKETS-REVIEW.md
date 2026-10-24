# DELIVERY-013-PM-LLM-POC-PI-EXECUTION-PACKETS-REVIEW

- **Date**: 2026-08-23
- **From**: LLM POC Team (M4b)
- **To**: User / POC Technical Lead; after User approval, Core Designer
- **Status**: `USER APPROVED / CORE PACKET ACK REQUEST`
- **Parent**: `ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001`

## Review package

This delivery presents two independent physical-Pi packets under one review cover:

1. `poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-006.md` — the bounded Gate 1 compatibility filter
   for the two Core-frozen candidates, with no Gate 2 credit.
2. `poc_llm/tests/gate2/GATE2A-PI-PACKET-001.md` — the full independent Pi 5 4GB LLM-only matrix,
   conditionally blocked until Core issues the Gate 1 Finalist ACK.

The combined review avoids two rounds of test-method negotiation while preserving the contractual
gate boundary. Core may accept/freeze both packet definitions in one response, but Gate 2A execution
authority becomes effective only after the separate Gate 1 result review and finalist ACK.

## Decisions frozen for review

- The only Pi inputs are Gemma 4 E2B and Qwen2.5 1.5B; there is no third backfill.
- Both stages use Raspberry Pi 5 4GB, Debian 13 aarch64 and `swap=0`.
- Gate 1 runs identity/offline-install/READY/PING/minimal generation/shutdown/cleanup only.
- Gate 2A independently reruns P1–P8, P10A, P11 and P12 with no evidence carry-over.
- P5's first model-backed formal execution occurs on the Pi at the fixed 15-second boundary. No
  workstation model execution is requested. Early valid completion is `INCONCLUSIVE`; the runner
  may not invent an easier fixture after seeing the result.
- P4 uses three fresh-process cold samples and one persistent process with three warmups plus twenty
  hot samples; thresholds remain negotiable as required by contract.
- P2/P3 uses the precommitted 20-case catalog ×3; P10A is a separate 20-session LLM-only soak.
- User approval remains mandatory before benchmark publication or a provisional candidate proposal.

## Executable implementation boundary

User has approved the test semantics. The packet implementation now includes the named Pi
controllers, PING/PONG protocol extension, Pi configs, public P5 fixture, result schemas and
checksum locks. It will receive only deterministic fake/local regression before the immutable
full-SHA Core review candidate is created. No model-backed P5 or scored Gate 1/Gate 2A command runs
on the workstation.

Core submission will request one packet-review response covering both definitions. Real execution
will still follow the two mandatory decision points: Gate 1 packet authorization, then Gate 1
Finalist ACK before Gate 2A.

## Requested Core ACK

Please return one written response that records the reviewed source commit and one disposition for
each item below:

1. `G1-PI-COMPAT-006`: `ACCEPTED FOR PHYSICAL-PI EXECUTION`, `REVISE`, or `REJECT`.
   An acceptance authorizes only the bounded Gate 1 compatibility command for the two named frozen
   candidates; it does not authorize a P1–P12 claim or Gate 2A.
2. `G2A-PI-LLM-001`: `PACKET FROZEN PENDING GATE-1 FINALIST ACK`, `REVISE`, or `REJECT`.
   An acceptance freezes the method and artifacts but does not authorize its command yet.

After a reviewed Gate 1 aggregate, Core must issue a separate finalist receipt that names each
authorized candidate and the Gate 1 evidence-manifest SHA. Only that receipt unlocks the independent
Gate 2A command for its named candidate. No response may infer a finalist, a benchmark result, or a
P5/P9 result from this review package.
