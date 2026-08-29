# DELIVERY-LLM-POC-M4B-GATE2A-PI-AUTH-001

- **Date**: 2026-08-29
- **From**: Core Designer
- **To**: LLM POC Team (M4b)
- **Status**: `GATE 2A PI EXECUTION AUTHORIZED / RESULT PENDING`
- **POC branch / exact SHA**: `llm` / `ed7aaca2e187b2287d442d6841e1ab2610b67570`
- **Gate 2A lock SHA-256**: `2a57754362d30d74c616a58a368bb79208493bc1fdb04b2cf1242c5b68fc683e`
- **Gate 2B lock SHA-256**: `5c89ca0b3499b8983361594ab41869872f189b1b410bf4f3333cac2a780fe775`
- **Gate 1 basis**: `DELIVERY-LLM-POC-M4B-GATE1-CLOSURE-ACK-001`

## Designer decision

Core verified that Independent Reviewer R4 approved the exact Gate 2 execution
surface without a development-readiness blocker, the POC milestone commit is
available unchanged at the full SHA above, and both lock digests reproduce the
reviewed identities. Gate 1 remains closed: Gemma is a normal finalist; Qwen
retains its immutable P7.1 `FAIL / SLOW_RECOVERY` score and advances only under
the recorded User defect waiver.

Core authorizes physical-Pi Gate 2A execution for both retained candidates. The
execution must use the locked packet and run only P2/P3/P4/P5/P8, with one clean
reboot and fresh evidence identity per candidate. Gate 1 P1/P6.1/P7.1/P10A/P11/P12
must be carried unchanged and must not be rerun to seek a different score.

## Boundaries and next handoff

This authorization is not Pi credit, benchmark publication, provisional
selection, Qwen workaround acceptance, Gate 2B authorization, final winner
acceptance or Core product baseline approval. Qwen cannot become the provisional
recommendation without a written Core/User workaround disposition that preserves
the ten-second P7.1 threshold and original FAIL result.

After both Gate 2A runs, submit the immutable result identities, sanitized
evidence checksums, cleanup/offline status and cumulative scorecard for User/Core
review. At most one provisional candidate may advance. Gate 2B remains blocked
until that decision and must then consume the Accepted Audio identity rather than
a surrogate.
