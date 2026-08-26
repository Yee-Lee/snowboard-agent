# REVIEW-LLM-M2-CUMULATIVE-REDESIGN-001

- **Date**: 2026-08-26
- **From**: Independent Reviewer
- **To**: LLM POC Technical Lead
- **Status**: `FEEDBACK PROVIDED / PENDING REVISIONS`
- **Target**: Gate 1, 2A, 2B Cumulative Redesign (`007`, Redesign Assessment, `006` Review)

## Overall Assessment

The redesign successfully addresses the `006` defect by decoupling the infrastructure I/O (model hashing) from the formal P1 (10-second READY) measurement.

However, after a rigorous re-evaluation, two **critical, high-risk logical flaws** remain in the testing workflow that will physically block execution and gate progression. These must be resolved before proceeding.

## Critical Issues & Improvement Directions

### 1. The Recursive Invalidation Trap (Source SHA Match)
- **Problem**: The cumulative matrix (`ASSESSMENT` & Gate 2A) explicitly mandates that Gate 1 evidence is carried forward *only* when the `full source SHA` matches exactly.
- **High Risk / Blocker**: Gate 2A requires the "Core-accepted G1-PI-COMPAT-007 cumulative receipt" as an entry condition. If this receipt, or the Core ACK document, is committed to Git, the repository's Git commit SHA changes. When Gate 2A subsequently runs, its `--execution-sha` will differ from the SHA recorded in the Gate 1 receipt. The strict "identity drift" rule will automatically invalidate Gate 1, forcing an endless rerun loop where Gate 2A refuses to carry forward the evidence.
- **Improvement Direction**: Redefine "source identity drift". The framework must tolerate evidence/documentation commits. Either exclude `docs/` and `evidence/` directories from the source SHA calculation, OR explicitly allow Gate 2A to accept the exact Git commit SHA that generated the Gate 1 receipt as a valid, trusted chronological parent without triggering regression.

### 2. P5 Timeout Process Deadlock (Fast Model Trap)
- **Problem**: Gate 2A (`002`) states that for P5, "Valid completion before 15 seconds is INCONCLUSIVE and requires a predeclared replacement disposition."
- **High Risk / Blocker**: Smaller models (e.g., Qwen2.5 1.5B Q8) may generate the 512-token extreme fixture in under 15 seconds on a Pi 5. If this happens, the framework will return a perpetual `INCONCLUSIVE`. Since no replacement disposition is declared in the packets, Gate 2A will be permanently blocked.
- **Improvement Direction**: Predeclare the replacement disposition immediately in the `002` packet. Either:
  1. Treat "graceful completion before the 15s timeout" as a `PASS` (since completing 512 tokens under 15s is an extreme performance success).
  2. Use a guaranteed-infinite output configuration (e.g., `max_tokens=null` or forcing continuous chunking) specifically for P5 so the timeout is mathematically guaranteed to hit.

## Next Steps
Please update the `007` and `002` packets and the assessment to patch these two structural automation blockers. All other minor or theoretical feedback has been dropped.
