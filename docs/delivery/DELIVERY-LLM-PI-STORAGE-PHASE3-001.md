# DELIVERY-LLM-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: LLM POC Team
- To: Core
- Request: `REQUEST-POC-LLM-PI-STORAGE-PHASE3-001`
- Feedback: `FEEDBACK-POC-LLM-PI-STORAGE-PHASE3-001`
- State: `SOURCE AND SMALL-FIXTURE RETURN READY / CORE REVIEW REQUIRED`

The corrected candidate binds tracked selected inputs to immutable product copies,
keeps model and wheel objects in a separate content-addressed artifact root, binds
runtime/native bytes, enforces model size, and keys XNNPACK cache objects over all
eleven required identities. It rejects mutable/scratch, symlinked, run-local,
overlapping and active/rollback-colliding paths.

Phase 1 inventory, 36 run checksums, the Phase 2 workspace receipt, protected-hold
migration and the 57-row post-download cleanup plan remain logical-locator records.
All cleanup rows are closed pending a verified local download receipt and their
class-specific replacement/preflight gates. No Pi hold changed.

The private evidence exporter matches Core's `list-ready --ready-root` and
`stream --ready-root --bundle-id` contract. Small fixtures prove traversal,
duplicate, symlink, missing-file and checksum rejection, exact list JSON, gzip tar
shape, SHA256SUMS coverage, and stdout purity.

Affected validation: the initial 26 tests passed in 0.252 seconds; after adding the
cleanup-plan gate test, the five-test curation module passed in 0.003 seconds. Pi bounded preflight verified
the clean `llm` workspace at the Phase 2 receipt SHA and three assigned writable
data roots, returning logical locators only with `model_loaded=false` and
`writes_performed=false`. The known five local child-cleanup baseline failures were
not rerun or relabeled. Frozen MVA surface verification is expected to remain open
because this source candidate has not entered the User-authorized snapshot/freeze
sequence.

Core's materialized topology was then incorporated and the 16 directly affected
layout/identity/curation/exporter tests passed in 0.249 seconds. Read-only Pi hashes
all match, with zero product symlinks. Canonical preflight remains blocked because
runtime/model/wheel hardlinks are writable mode `0664`; changing them would also
change retained active inodes. The private ready bundle
`llm-phase1-m4b-runs-20260906` lists 11,331,163 estimated bytes and maps to
13,000,704 allocated bytes of historical runs after receipt and cleanup gates.

Core has since accepted the canonical verifier, downloaded and verified the private
bundle, removed the 36 legacy run paths and ready tree, and created the logical
current product binding. The User authorized this candidate's governed commit/push;
LLM owns the subsequent snapshot/freeze and target M4B-MVA execution.
