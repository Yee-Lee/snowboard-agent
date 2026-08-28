# REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R3-001

- **Date**: 2026-08-28
- **From**: LLM POC Designer / Technical Lead
- **To**: Independent Reviewer
- **Status**: `TARGETED RE-REVIEW REQUEST / PI NOT AUTHORIZED`
- **Reviewed base**: `0638f5ad859627014f7cf0d57882ac394b100466` plus this R3 replacement worktree
- **Gate 2A lock SHA-256**: `e8eaebcbc8c69bb85b94b7491f945b01b353ae30c45d0244ea7d147b5c674aab`
- **Gate 2B lock SHA-256**: `a95f9669bc4caa17a7fbd14242f48a54a02411c9fd8b0972a6a9758be21ca910`
- **Responds to**: `docs/reviews/REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R2-001.md`

## Scope

This replacement changes only R2-F1 through R2-F3. It does not reopen closed F1/F5 from the
original review, expand Audio/model scope, execute Pi credit, publish benchmark results or propose
a candidate.

## R2-F1 — P5 completion/cancel arbitration

`LiteRtContinuousBackend._chunk()` now performs one final lock-protected arbitration after
generation and metrics but before `chunk_completed`. Cancel-first leaves the chunk incomplete and
uses exactly one native cancel. Completion-first clears the active conversation and changes state to
`BETWEEN_CHUNKS` before declaring completion, so later cancel uses zero native cancels. Deterministic
barriers immediately before and after arbitration assert the full marker set, TIMEOUT terminal,
same-child health and rebuild behavior. The completed-plus-native-cancel third mode is no longer
reachable.

## R2-F2 — Actual scored protocol classification

Both runners now wrap the actual post-READY `generate()` path. Deadline, EOF, invalid JSONL and
protocol-invalid frames become `CandidateViolation`; pre-READY startup, filesystem, evidence,
sampler and probe failures retain `INCONCLUSIVE`. Gate 2A applies the same typed boundary to the P5
PING/health/rebuild/shutdown paths and distinguishes candidate failures from observation errors.
Gate 2B's entered LLM request path uses the same mapping, producing P10B `FAIL` while sampler/probe
faults remain `INCONCLUSIVE`.

## R2-F3 — Partial-start owner cleanup

The coordinator registers each domain before awaiting `start()`, captures a valid live root after
each successful start, and also recovers a root when `start()` raises after allocation. Cleanup runs
in reverse over every attempted domain and invokes bounded owner fallback whenever a captured live
group survives cooperative stop. The runner now preserves partial trace, roots and cleanup proof
even when full residency/sampling was never entered. Tests cover a later start failure plus earlier
stop failure, and start-raises-after-becoming-live.

## Verification

- Gate 2 workstation suite: `55/55 PASS` (the prior 49 plus six targeted R3 tests).
- Gate 1 regression suite: `136/136 PASS`.
- Pi execution: not performed and not authorized by this request.
- Publication/candidate proposal: not performed.

The User's standing workflow requires reviewer approval before the milestone commit. Therefore this
request identifies one exact replacement worktree and lock pair on the reviewed base; the clean
milestone commit will be created only after approval and will not alter the authenticated execution
surface.

## Requested decision

Review only the three R2 findings and return `APPROVE` or exact remaining blocking defects. Approval
authorizes the milestone commit/push step; it does not itself authorize Pi execution or result
publication.
