# FEEDBACK-POC-LLM-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: Core review
- To: LLM POC Team
- Request: `REQUEST-POC-LLM-PI-STORAGE-PHASE3-001`
- Status: `BLOCKING — REVISE AND RETURN`

## Findings

1. **Blocking — Git identity validation is incorrect.** Workspace preflight uses a
   64-character content-digest validator for the required 40-character Git SHA, so
   an otherwise valid receipt is always blocked. Add a distinct full-Git-SHA
   validator and positive/negative tests.
2. **Blocking — cache backend test does not reach the behavior.** The fake LiteRT
   module does not expose `Backend`; the test fails before it can verify `cache_dir`.
   Repair the fixture and prove the exact cache path reaches the engine constructor.
3. **Blocking — Phase 3 regression is red.** The review run reports 31 passed and
   seven failed. The two deterministic Phase 3 failures must be zero. Classify the
   five existing environment/child-cleanup failures using a reproducible baseline;
   do not report the suite as green.
4. **Blocking — protected surface changed.** Source changes invalidate the existing
   MVA surface lock. Do not run target measurements or silently refresh a frozen
   lock. Finish the reviewable source/tests and return a new candidate commit
   proposal for User authorization, then repeat the governed snapshot/portable/
   freeze sequence.
5. **Blocking — migration manifest is missing.** `product-storage-v1.json` defines
   the selected product identity but does not enumerate all protected Phase 1 holds.
   Add a manifest with source logical locator, target artifact/product identity,
   digest/size where known, `verify-only` action, materialization state, and hold
   state for every protected input.
6. **Blocking — native runtime identity is declared but not verified.** Bind the
   native library path and compare its actual bytes to the fixed digest when
   preparing and verifying the runtime receipt. Add a mismatch test.
7. **Blocking — governing receipt is absent.** Copy the exact Core
   `RECEIPT-PI-PHASE2-WORKSPACES-001.md` into the read-only incoming handoff area.
   The team's ACK is a response and cannot replace the governing input.
8. **Blocking — status documents contradict execution.** Update the milestone index
   that still says Pi inventory was not executed. Preserve the open MVA measurement,
   acceptance, and attempt 005 evidence gaps.
9. **Blocking — commit proposal is incomplete.** Replace the Phase 1/2-only proposal
   with one exact proposal covering Phase 1/2/3 source, tests, migration manifest,
   receipt, reconciliation, and this feedback response. Exclude unrelated owner
   changes and do not commit or push before User confirmation.

## Required return

Return the corrected files, exact affected-test commands/results, reproducible
classification of any environment-only failures, bounded workspace preflight, Git
privacy/whitespace checks, remaining open milestone work, and the full proposed
commit title, body, and file list. Model loading, benchmark execution, product
materialization, service activation, hold movement, and cleanup remain unauthorized.
