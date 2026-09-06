# REQUEST-POC-LLM-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: Core
- Owner: LLM POC Team
- Status: `OPEN — IMPLEMENTATION AND VALIDATION REQUIRED`
- Inputs: `RECEIPT-PI-PHASE2-WORKSPACES-001` and
  `DELIVERY-LLM-PI-CURATION-POSTCHECK-001`
- Baseline: `llm` / `7a56137b7b2d65219ea4ff2065ab2773c179a0af`

## Authorization and outcome

The User directed Core to return a new task and have the LLM team complete it.
Implement the storage/path changes needed to bind a stable M4B product, one
content-addressed model, and a correctly keyed generated cache without per-run
copies. Finish with reviewable source, tests, a migration manifest, reconciled
curation documents, a return handoff, and a complete commit proposal.

## Required work

1. Bind the selected profile and schema to a stable tracked/product locator. Bind
   the isolated runtime by inventory identity and the large model by digest.
2. Keep the model outside runtime and run trees. Key generated accelerator cache by
   model digest/size, runtime digest/API revision, device ABI, backend/delegate
   settings, and cache-format revision.
3. Reject mutable/scratch locators, identity mismatch, run-local large inputs, and
   active/rollback cache collision.
4. Produce a logical-locator migration manifest covering every current M4B hold and
   its intended canonical product/artifact identity. Do not move, hardlink,
   quarantine, or delete those inputs in this phase.
5. Add meaningful tests using temporary directories and small fixtures. Preserve
   existing MVA owner edits and original machine outcomes.
6. Reconcile the old curation ACK with the completed inventory using an explicit
   superseded marker. Keep attempt 005 and unfinished MVA measurement/acceptance
   open.
7. On the Pi canonical LLM worktree, perform only bounded workspace/preflight checks
   without model loading or bulky output.
8. Return exact changed files, validation commands/results, overlaps or remaining
   risks, and a proposed commit title, body, and file list after reading the LLM
   workflow.

## Limits

Filesystem utilization is 78%. Do not create a new model/runtime/venv copy, execute
a benchmark, activate a service or `current` pointer, modify another team's roots,
move a protected hold, or purge data. Use logical locators in public files. Do not
commit or push until the User approves the complete proposal.

## Acceptance

Tests establish stable product/profile/model/runtime/cache identity without per-run
large copies; the migration manifest covers protected inputs without moving them;
the curation state is internally consistent; the new Pi workspace remains clean
except for the explicitly returned source change set; and no private environment
details enter Git.
