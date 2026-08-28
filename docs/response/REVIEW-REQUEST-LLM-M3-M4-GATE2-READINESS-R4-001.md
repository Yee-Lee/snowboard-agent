# REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R4-001

- **Date**: 2026-08-28
- **From**: LLM POC Designer / Technical Lead
- **To**: Independent Reviewer
- **Status**: `TARGETED RE-REVIEW REQUEST / PI NOT AUTHORIZED`
- **Reviewed base**: `0638f5ad859627014f7cf0d57882ac394b100466` plus this R4 replacement worktree
- **Gate 2A lock SHA-256**: `2a57754362d30d74c616a58a368bb79208493bc1fdb04b2cf1242c5b68fc683e`
- **Gate 2B lock SHA-256**: `5c89ca0b3499b8983361594ab41869872f189b1b410bf4f3333cac2a780fe775`
- **Responds to**: `docs/reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R3-001.md`

## Scope and retained closures

This replacement changes only R3-F1 and R3-F2. R2-F3 and original F1/F5 remain unchanged. It does
not expand Audio/model scope, run Pi credit, publish benchmarks or propose a candidate.

## R3-F1 — Native cancel lifetime and outcome

The P5 backend now uses a `Condition` on its state lock. Cancel-first reserves the active
conversation with `_native_cancel_in_flight`; finalization waits before clearing or closing it. The
native call executes without holding the lock, then publishes exactly one post-call outcome:
`native_cancel_once` after success or `native_cancel_failed` after exception. Only then is
finalization released. Active PASS requires one success and zero failure markers; boundary PASS
requires both zero.

The lifetime test blocks inside the native call, independently releases generation finalization,
proves the conversation remains open, then releases native cancel and proves one close with no
live/error thread. Its injected-failure branch proves zero success markers, one failure marker,
eventual close and P5 FAIL. The completion-first control retains zero native outcomes.

## R3-F2 — Scored pipe matrix and stage precedence

Both scored GENERATE boundaries translate only `PiPacketFailure`, `BrokenPipeError`,
`ConnectionResetError` and invalid text decoding into `CandidateViolation`. P5 PING uses the same
narrow tuple; scored shutdown additionally translates `subprocess.TimeoutExpired`. Generic probe,
sampler, filesystem and pre-READY `OSError` paths remain `INCONCLUSIVE`.

P5 adjudicates the complete primary stage first. A primary FAIL or INCONCLUSIVE returns immediately
and cannot be overwritten by rebuild. Rebuild candidate/observation/health is considered only after
primary PASS. The independent evidence verifier calls the identical two-stage function, and the
full precedence table executes through both paths.

## Protocol integration and verification

The fake backend is exercised through `PiChild` with a controlled short outer timer. Cancel-first
and completion-first both produce correlated `ERROR/TIMEOUT`, mutually exclusive marker modes,
same-child PING/generation health, fresh rebuild health and clean shutdown.

- Gate 2 workstation suite: `59/59 PASS`.
- Gate 1 regression suite: `136/136 PASS`.
- Changed bytecode compilation, both fatal-outcome self-tests, `git diff --check` and both lock
  artifact checks: `PASS`.
- Pi execution/publication/candidate proposal: not performed.

The User requires reviewer approval before the milestone commit. This exact worktree and lock pair
are submitted for targeted review; approval authorizes commit/push, not Pi execution or publication.

## Requested decision

Review only R3-F1 and R3-F2 against the R3 sufficiency table and return `APPROVE` or an exact
remaining blocker.
