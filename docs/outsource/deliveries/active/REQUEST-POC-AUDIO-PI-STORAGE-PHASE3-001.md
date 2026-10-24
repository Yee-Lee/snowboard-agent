# REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: Core
- Owner: Audio POC Team
- Status: `OPEN — IMPLEMENTATION AND VALIDATION REQUIRED`
- Inputs: `RECEIPT-PI-PHASE2-WORKSPACES-001` and
  `PI-STORAGE-CURATION-PHASE3-PLAN-001`
- Baseline: `audio` / `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`

## Authorization and outcome

The User directed Core to return a new task and have the Audio team complete it.
Implement the storage/path changes needed to use the provisioned workspace without
repeating large immutable inputs in each run. Finish with reviewable source, tests,
a migration manifest, a return handoff, and a complete commit proposal.

## Required work

1. Separate mutable run output, temporary evidence export, and reacquirable cache
   from the immutable M4A product contract.
2. Prevent runners/installers from copying models, runtime trees, or virtual
   environments into each run. Preserve isolated VAD and TTS runtimes.
3. Make product identity and dependency validation explicit and fail closed. Do not
   make production configuration depend on a run or historical worktree.
4. Produce a logical-locator migration manifest for every currently held input and
   its intended canonical product/artifact identity. This phase verifies the plan;
   it does not move, hardlink, quarantine, or delete the held input.
5. Add meaningful unit/integration coverage using temporary directories and small
   fixtures. Verify wrong identity, mutable input, forbidden run dependency, and
   duplicate-large-input behavior.
6. On the Pi canonical Audio worktree, perform only bounded workspace/preflight
   checks that do not load a model or generate bulky output.
7. Return exact changed files, validation commands/results, remaining risks, and a
   proposed commit title, body, and file list after reading the Audio workflow.

## Limits

Filesystem utilization is 78%. Do not create a new model/runtime/venv copy, execute
a benchmark, activate a service or `current` pointer, modify another team's roots,
move a protected hold, or purge data. Use logical locators in public files. Do not
commit or push until the User approves the complete proposal.

## Acceptance

Core can trace a run to one immutable product identity; tests prove large inputs are
not materialized per run; the migration manifest covers all active holds without
moving them; the new Pi workspace remains clean except for the explicitly returned
source change set; and no private environment details enter Git.
