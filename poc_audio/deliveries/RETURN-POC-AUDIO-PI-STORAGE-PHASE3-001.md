# RETURN-POC-AUDIO-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: Audio POC Team
- To: Core
- Request: `REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001`
- Status: `AUDIO FEEDBACK CLOSED / CORE RE-REVIEW AND ROOT DECISION REQUIRED`
- Base SHA: `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`

Phase 3 adds fail-closed storage bindings for the assigned run, evidence, and
cache roots. Formal M4 execution now requires distinct roots, refuses immutable
inputs below the run root, and records logical storage identity in results.
Matcha and historical qualification consume one read-only product model keyed
by the source archive SHA-256 instead of extracting a model into every run.
Artifacts and isolated runtime interpreters must belong to the same complete
verified product root and are never copied. Reacquirable cache content cannot
become a formal execution dependency.

The migration manifest maps every Phase 1 hold to an intended product, evidence,
private-data, or content-object identity. Every action is `VERIFY_ONLY`;
movement, hardlinks, quarantine, activation, and deletion remain unauthorized.
The private-evidence exporter implements Core's JSON listing and streamed gzip
tar contract without staging an archive on Pi. The post-download cleanup
manifest records exact logical locators and receipt/preflight gates. Recorded
expected archive values are not accepted as a Core receipt by themselves; no
cleanup target becomes actionable without the separate verified receipt and
reference conditions.

Local tests use temporary directories and small fixtures to cover correct reuse,
wrong identity, mutable input, aliased roots, run-owned dependencies, and absence
of duplicated model content. Pi validation is limited to the clean canonical
worktree, assigned-root permissions, packet validation, and disk high-water
observation. No model was loaded and no benchmark or bulky output was created.

Private payloads are prepared only below
`PI_AUDIO_PRIVATE/<bundle-id>` with owner-only permissions. The exporter verifies
the manifest and every payload before streaming a gzip tar; it writes no archive
on the Pi. `PI_DEV_ROOT/evidence-export/audio` is reserved for sanitized export
material and must not receive raw audio, transcripts, comments, or content logs.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=poc_audio/src python3 -m unittest
  poc_audio.tests.test_m4_storage poc_audio.tests.test_export_private_evidence
  poc_audio.tests.test_verify_cleanup_plan poc_audio.tests.test_m4_combined
  poc_audio.tests.test_m4_combined_coordinator`: 42/42 passed (18 storage,
  seven private-export, three cleanup-receipt, 14 M4 regression cases).
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=poc_audio/src python3 -m unittest
  discover -s poc_audio/tests -p 'test_*.py'`: 242 tests; 235 passed and seven
  were unavailable on this workstation. Six require NumPy and one requires
  Linux `/proc`; none exercises a Phase 3 changed behavior.
- Updated Python modules compiled with bytecode redirected to a temporary root;
  both shell entry points passed `bash -n` and `git diff --check` passed.
- The Core privacy scanner passed every file in this proposal. Both incoming
  Core documents are byte-for-byte exact copies; all four JSON manifests parse.
- Pi packet-only preflight: exact clean `audio`/`audio_m4` baseline, 20 sessions,
  12 failure cases, formal execution disabled, assigned roots mode `0750`, 78%
  filesystem use, and clean worktree before and after.
- A repeated read-only Pi check found no READY manifest below
  `PI_AUDIO_PRIVATE`; no private bundle was streamed by Audio. Core's migration
  status still marks the external archive receipt as waiting, so values recorded
  in the cleanup plan are not treated as accepted receipt evidence. Cleanup
  dry-run returned an empty eligible set.
- Core downloader/privacy tests passed 11/11. Cross-team inspection found its
  Audio ready-root binding still points at the shared evidence-export root;
  `CR-AUDIO-PI-PRIVATE-EVIDENCE-ROOT-001` requests an operator-private mapping
  before any real bundle is selected.
- The cleanup verifier consumes Core's receipt field names,
  `archive_sha256` and `archive_bytes`.
- Cross-team product inspection found that Core's existing
  `sbd.m4a.product-install.v4` layout does not directly provide Audio's required
  marker, file inventory, or hash-keyed model identities.
  `CR-AUDIO-PI-PRODUCT-CONTRACT-001` requests one canonical schema or a
  deterministic no-copy adapter before materialization.

## Blocking feedback closure

1. The Core request and feedback are retained as exact incoming copies; team
   status stays in this response and the Phase 2 ACK.
2. Product verification hashes the actual manifest, validates every dependency
   byte/size/mode and the read-only product tree, requires runtime/native
   inventories, rejects nested roots, and rejects symlink components.
3. Formal TTS no longer reads candidate archives or wheels; all formal
   artifacts, runtimes, native files, models, and vocoder belong to one product.
4. Qualification shell and README invocations include the product root and
   model layout.
5. This return contains commands, results, files, risks, and commit proposal.
6. Tests cover concurrency, shared read-only product, evidence separation,
   manifest/runtime/native mismatch, nesting, symlinks, cache rejection, and
   archive safety.
7. Cache is reacquirable only and never a formal dependency.

## Changed files

- `docs/pm_handoff/ACK-POC-AUDIO-PI-PHASE2-WORKSPACES-001.md`
- `docs/pm_handoff/FEEDBACK-POC-AUDIO-PI-STORAGE-PHASE3-001.md`
- `docs/pm_handoff/REQUEST-POC-AUDIO-PI-STORAGE-CURATION-001.md`
- `docs/pm_handoff/REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001.md`
- `poc_audio/deliveries/PI-STORAGE-CURATION-PHASE3-PLAN-001.md`
- `poc_audio/deliveries/CR-AUDIO-PI-PRODUCT-CONTRACT-001.md`
- `poc_audio/deliveries/CR-AUDIO-PI-PRIVATE-EVIDENCE-ROOT-001.md`
- `poc_audio/deliveries/RETURN-POC-AUDIO-PI-STORAGE-CURATION-001.md`
- `poc_audio/deliveries/RETURN-POC-AUDIO-PI-STORAGE-PHASE3-001.md`
- `poc_audio/evidence/PI-STORAGE-CURATION-EVIDENCE-INDEX-001.json`
- `poc_audio/manifests/pi_storage_cleanup_001.json`
- `poc_audio/manifests/pi_storage_phase3_migration_001.json`
- `poc_audio/manifests/pi_storage_post_download_cleanup_001.json`
- `poc_audio/README.md`
- `poc_audio/src/audio_poc/m4_combined_domains.py`
- `poc_audio/src/audio_poc/m4_formal.py`
- `poc_audio/src/audio_poc/m4_storage.py`
- `poc_audio/src/audio_poc/m4a_qualification.py`
- `poc_audio/tests/test_m4_storage.py`
- `poc_audio/tests/test_export_private_evidence.py`
- `poc_audio/tests/test_verify_cleanup_plan.py`
- `poc_audio/tools/export_private_evidence.py`
- `poc_audio/tools/run_m4_combined.sh`
- `poc_audio/tools/run_m4a_qualification.sh`
- `poc_audio/tools/verify_cleanup_plan.py`

## Commit proposal

Title:

`[feat][M4]: bind audio runners to verified storage`

Body:

- Require separate run, evidence, cache, and verified product roots.
- Add private export, cleanup planning, curation evidence, and workspace receipts.

Files: the exact changed-file list above.

Remaining work requires separate review: materialize the complete read-only M4A
product and its manifest from installer inputs; migrate retained evidence only
after manifest review; download and verify a ready private bundle when one
exists; recheck all references; and obtain separate User approval before any
purge. Cache remains limited to reacquirable download and build inputs.

Private download additionally waits for Core to resolve
`CR-AUDIO-PI-PRIVATE-EVIDENCE-ROOT-001`; shared evidence export cannot be used as
the raw private ready root.

Product materialization additionally waits for Core to resolve
`CR-AUDIO-PI-PRODUCT-CONTRACT-001`; Audio will not copy or reshape the accepted
Core install speculatively.
