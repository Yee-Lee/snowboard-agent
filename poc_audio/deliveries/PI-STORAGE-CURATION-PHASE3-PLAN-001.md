# PI-STORAGE-CURATION-PHASE3-PLAN-001

Status: `IMPLEMENTED LOCALLY / FEEDBACK REVISION VALIDATED / CORE RE-REVIEW PENDING`

This plan records Audio-owned runner and storage changes needed after Core
provisions the canonical Pi layout. It does not bind a new path, create a
worktree, move an artifact, or alter an accepted result.

## Phase 2 workspace receipt

Core provisioned and Audio verified the clean `PI_DEV_ROOT/audio` worktree at
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`. Audio may use only
`PI_DEV_ROOT/runs/audio`, `PI_DEV_ROOT/evidence-export/audio`, and
`PI_DEV_ROOT/cache/audio` for development data. Filesystem utilization was 78%
at receipt, so no nonessential benchmark, virtual environment, model/runtime
copy, or bulky output is authorized. Phase 1 holds and purge boundaries remain
in force.

The reacquirable cache is never a formal model or runtime dependency. Formal and
qualification runners bind immutable inputs to one complete verified product
root. Its real materialization remains a later Core-owned review step.

## Required behavior

1. Resolve every model, voice, source archive, wheelhouse, and native binary by
   immutable SHA-256 from the Core-provisioned artifact root.
2. Keep those objects read-only. A run receives verified paths and must not copy
   or extract the same object into every domain/case directory.
3. Key Python environments by lock hash, Python ABI, architecture, and platform.
   Reuse an exact closed environment only after its package and native-library
   inventory validates.
4. Key native builds by source SHA, compiler identity, flags, architecture, and
   output checksum. Build scratch remains disposable.
5. Keep run directories small: authorization, packet/fixture locks, stdout and
   stderr, raw/result JSON, network trace, cleanup proof, and references to
   immutable artifacts. Raw/private evidence remains controlled.
6. Finalization must fail closed if a referenced artifact disappears, changes
   checksum, points outside a provisioned root, or if result preservation fails.
7. Retain accepted, rejected, and inconclusive dispositions independently of
   scratch cleanup. A local payload saying `PASS` never overrides a governing
   rejected-evidence record.

## Implemented Audio files

- `poc_audio/src/audio_poc/m4_storage.py`: validates distinct assigned roots,
  rejects run-owned or cache-backed immutable inputs, and verifies read-only
  product models by source archive SHA-256.
- `poc_audio/src/audio_poc/m4a_qualification.py`: consumes shared ASR/TTS
  expansions keyed by archive SHA instead of extracting into a run directory.
- `poc_audio/src/audio_poc/m4_combined_domains.py`: consumes the verified
  shared Matcha expansion without per-domain or per-case extraction.
- `poc_audio/src/audio_poc/m4_formal.py`: requires provisioned run, evidence,
  cache, and Matcha expansion paths and records their logical object identity.
- `poc_audio/tools/run_m4_combined.sh`: exposes the required run, evidence,
  cache, product, and model bindings in formal-mode usage.
- `poc_audio/tools/run_m4a_qualification.sh`: exposes the verified product root
  while keeping reacquirable qualification archives in cache.
- `poc_audio/tools/export_private_evidence.py`: lists and streams owner-only
  private bundles as gzip archives without staging another Pi copy.
- `poc_audio/tools/verify_cleanup_plan.py`: emits a dry-run eligible set only
  after a nonempty exact archive receipt and all preflight conditions match.
- `poc_audio/tests/test_m4_storage.py`: covers reuse, wrong identity, mutable
  input, root aliasing, run dependency, and absence of per-run model content.
- `poc_audio/tests/test_export_private_evidence.py` and
  `poc_audio/tests/test_verify_cleanup_plan.py`: cover private archive safety and
  receipt-gated cleanup planning.
- `poc_audio/manifests/pi_storage_phase3_migration_001.json`: maps protected
  current inputs to intended canonical identities without authorizing movement.

Existing accepted packet hashes remain immutable; Phase 3 does not revise the
packet or its schemas.

Private evidence stays at `PI_AUDIO_PRIVATE/<bundle-id>` with owner-only
permissions. Only the streamed archive receipt and a sanitized public projection
may leave that boundary; raw private content never enters Git or the shared
evidence-export root.

## Required tests

- One physical model object serves P9.1, combined, and all twelve failure cases.
- Two runs with the same artifact and runtime locks create no second model or
  virtualenv payload.
- A checksum mismatch, missing object, writable artifact, or path escape fails
  before model load.
- Concurrent runs cannot mutate or partially extract a shared object.
- Scratch cleanup cannot remove a retained result, authorization, fixture lock,
  network trace, or controlled locator.
- Accepted, rejected, and inconclusive fixture payloads survive scratch cleanup.
- `d36490f...` remains rejected evidence even though its original result JSON
  contains `PASS`.
- Runtime identity includes Python ABI, exact packages, native libraries, and
  offline reconstruction proof.
- Existing M2A/M2B scorecard and M4 result validators remain green.

## Exit conditions

- The acknowledged Core workspace receipt continues to name the logical roots,
  owners, permissions, and migration order.
- The protected M4A product is reproduced from the provisioned stores and its
  acceptance dependencies are self-contained.
- An exact before/after inventory proves no disposition or only-copy input was
  lost.
- Core reviews the cleanup manifest and the User separately approves permanent
  purge targets.
