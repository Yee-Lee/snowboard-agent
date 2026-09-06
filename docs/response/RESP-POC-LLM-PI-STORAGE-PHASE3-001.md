# RESP-POC-LLM-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: LLM POC Team
- To: Core review
- Request: `REQUEST-POC-LLM-PI-STORAGE-PHASE3-001`
- Feedback: `FEEDBACK-POC-LLM-PI-STORAGE-PHASE3-001`
- State: `CORRECTED CANDIDATE / CORE REVIEW REQUIRED`

## Finding disposition

1. Workspace preflight now uses a distinct 40-character lowercase `GIT_SHA_RE`.
   Positive and malformed-length/case/alphabet tests pass.
2. The fake LiteRT module exposes `Backend`; the test proves the exact
   content-addressed `cache_dir` reaches `Engine`.
3. The initial 26 affected small-fixture tests pass; the added cleanup-plan gate
   test also passes in the five-test curation module. The five earlier controller failures
   remain the pre-existing local child-owner census/cleanup limitation; they are
   not reported as green and the full suite was not repeated under the deadline.
4. The source surface changed intentionally. The frozen lock was not updated and
   no target measurement ran. A new candidate commit requires User approval before
   the governed snapshot, portable validation, and freeze sequence.
5. `protected-hold-migration-v1.json` covers every Phase 1 protected-hold string
   and records source/target identity, digest/size or explicit unknown, action
   `verify-only`, `materialized=false`, and `hold=true`.
6. Product config binds the physical native-library path. Product validation and
   install-receipt preparation/verification compare its actual bytes to the fixed
   digest; mismatch coverage passes.
7. The exact Core Phase 2 receipt and this exact feedback are present in the
   read-only incoming handoff directory.
8. The milestone status records completed inventory/workspace preflight while
   leaving Attempt 005, MVA measurement/acceptance, migration acceptance, and purge
   open.
9. The candidate proposal covers Phase 1/2/3, exporter, migration/cleanup manifests,
   receipts, reconciliation, tests, and this response. Unrelated owner edits remain
   excluded.

## Added download and cleanup contract

`export_private_evidence.py` implements Core's exact interface. `list-ready` writes
one path-private JSON object to stdout. `stream` writes only gzip tar bytes to
stdout and diagnostics to stderr. It preflights mode-private manifests, checks
bundle identity, sizes and SHA-256, and rejects missing files, symlinks, non-regular
files, duplicate/unsafe archive names, and traversal. The archive contains only
regular files/directories, with root `manifest.private.json`, root `SHA256SUMS`, and
payload below `payload/`; sums cover the manifest and every payload file.

The post-download cleanup manifest expands 57 exact logical locators into three
gates: receipt-ready historical material, current inputs requiring canonical
materialization/preflight, and unresolved holds. Every row remains
`delete_after_verified_receipt=false`; no cleanup is authorized. Worktrees require
standard Git worktree commands.

## Execution boundary

LLM materialized no model/runtime/product. Core's newly materialized candidate was
checked read-only: every fixed digest and size matched and zero symlinks were found.
Profile/schema copies are mode `0440`; runtime/model/wheel hardlinks are mode `0664`
with link count two, so immutable-product preflight remains blocked. Changing those
inodes would also change old active inputs, so LLM made no permission change. The
ready bundle `llm-phase1-m4b-runs-20260906` covers 36 runs/438 files; `list-ready`
reports 11,331,163 estimated bytes without creating an archive.

Core subsequently verified the downloaded archive at SHA-256
`a5adfb2bf9b7ad389b2cbdecf076949ddc6fad2adb7c387979923c0509bdd7b5`,
removed the 36 legacy run directories and ready export tree, accepted the immutable
canonical verifier, and bound `PI_PROD_PRODUCTS/m4b/current` to product `8279e79`.
LLM ran no cleanup. No benchmark or MVA target measurement has run yet; LLM now
continues the governed candidate/snapshot sequence under the User's commit/push
authorization.
