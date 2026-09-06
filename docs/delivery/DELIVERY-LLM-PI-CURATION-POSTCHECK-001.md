# DELIVERY-LLM-PI-CURATION-POSTCHECK-001

- Date: 2026-09-06
- State: PHASE 1 COMPLETE / CORE PHASE 2 WORKSPACE RECEIPT VERIFIED / NOT RELAYED
- Governing income: `REQUEST-POC-LLM-PI-STORAGE-CURATION-001`
- Local base: `57390cc1ed7aef7a3a172716bb71e622649c4f67`
- No new commit, push, benchmark publication or milestone transition.

## Delivery contribution and authority

This work advances reproducible M4b source/profile/artifact handoff and discoverability of
retained evidence. User explicitly authorized SSH and LLM organization after the local MVA
checkpoint. This does not authorize MVA measurement, reboot, Core/Audio changes, Phase 2
provisioning, Phase 3 runner rebinding or permanent purge.

The concurrently added pre-check files were reconciled without changing their historical
observation values:
`pi-storage-worktree-inventory-v1.json`, `pi-cleanup-manifest-v1.json`,
`llm-result-index-v1.json` and `HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001.md`.
They describe an earlier observation. This supplement supersedes their statements that no
checkout occurred and that the current Pi LLM checkout remains detached. It does not independently
approve their historical result conclusions, private-bundle existence or reclaim estimates.
The local-intake ACK's earlier “Pi not executed” statement is explicitly marked superseded.

Core subsequently issued its Phase 2 workspace receipt. Read-only verification confirms
`PI_DEV_ROOT/poc_llm` on clean `llm` at
`7a56137b7b2d65219ea4ff2065ab2773c179a0af`, with matching `origin/llm`, plus writable non-symlink
directories at `PI_DEV_ROOT/runs/poc_llm`, `PI_DEV_ROOT/evidence-export/poc_llm` and
`PI_DEV_ROOT/cache/poc_llm`. No Phase 3 write or benchmark occurred. Filesystem use remains 78%,
so nonessential benchmarks, bulky output and duplicate venv/model/runtime inputs are prohibited.

## Actual Pi actions and final state

Only the existing LLM checkout was changed: fetched existing `origin`'s published `llm` and
`llm_m4` refs, switched the clean checkout to its existing `llm` branch with
`--no-overwrite-ignore`, and fast-forwarded it. No local unpublished MVA code was transferred.
Remote URL was checked against the workstation origin; the endpoint is intentionally omitted.
Git also auto-followed an Audio tag as metadata; no Audio checkout or file was modified.

- Logical checkout: `PI_LLM_WORKSPACE/snowboard-agent`.
- Before: detached `e2b59fac609e0d768ff3554754363900cbed70a9`;
  existing local `llm` was `afb310b5337857e01741ab455086b53f9904f280`.
- After: branch `llm`, HEAD and `origin/llm`
  `7a56137b7b2d65219ea4ff2065ab2773c179a0af`; tracked clean, zero untracked files.
- Tag object: `1b9ece39c77932cd2f92c1739ec2b38d83dece71`;
  peeled completion: `b5ce101d1f75889bfcc1bf6f38ed563f59c2d9a1`.
- Accepted execution `0c75536e6ee99b502c59438989ca852194648946`, closure
  `5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae`, publication
  `485bb2a7c07d86a09899f09358c744edd733f875` and completion remain ancestors.

All 11 historical worktrees, including their untracked/ignored contents, remain intact.
No source history was reset, amended or rewritten. No new worktree, repository, service,
deployment root, permission change, activation pointer or data deletion was performed.
Expired scratch-worktree metadata was checked with Git's dry-run only; actual retirement remains open.

## Reviewable post-check files

- [Post-check inventory](../../poc_llm/curation/pi-storage-postcheck-v1.json):
  SHA-256 `59a0b1cc02749de7bc692385c6ec435a247a07b567bda7651d3b475ecb5c73b5`.
- [Exact path hold manifest](../../poc_llm/curation/pi-cleanup-postcheck-v1.json):
  SHA-256 `374622b745d1b79fd1348fc48b48d709f59c4a9f3ea85582049557ffeba19521`.
- [Stable selected profile/schema locators](../../poc_llm/curation/selected-profile-locators-v1.json).
- [Historical result index, concurrent draft pending reconciliation](../../poc_llm/curation/llm-result-index-v1.json).

The post-check covers 53 top-level directories across the four named roots, including 36 Core
run directories and all 11 historical worktrees. All 438 regular evidence files in those run
directories have individual checksums. Only allowlisted declared status fields are copied;
component/preflight PASS and directory names are not promoted to overall acceptance. Overall
result remains null in this storage index. No new measurement or revision to legacy machine
FAIL/INCONCLUSIVE/waiver semantics is made.

Observed regular-file apparent and unique bytes are both 3,919,743,886; inode-deduplicated
allocated bytes are 3,937,583,104. These are scan counts, not exclusive reclaimable allocation.
The scan excludes root-level non-directory entries and shared caches outside these roots, does
not follow external symlinks, and is not an atomic filesystem snapshot.

Three runtime trees were fully file-hashed: only `install-inventory.json` and `pyvenv.cfg`
differ across their regular-file lists. Matching payload hashes do not prove identical complete
installations or make installation-specific metadata disposable. Model/cache full checksums were
not repeated by this collector; previous recorded identities are not represented as newly verified.
The selected profile was independently hashed in both the updated checkout and protected
`gate2b-contained-00e6ae1`: both are
`c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e`.
Core should use the accepted publication's tracked locators, not substitute the newer MVA protocol.

The private source observation remains outside Git and has SHA-256
`f1c2f0b92a7dbf0c4e820149af43a6c1f6899b4b47a9f80dc8c77968a7c1c2ac`.
It is held in workstation temporary storage, not a verified durable evidence archive. Public
post-check files use logical locators and omit SSH endpoint/operator-home mappings and raw results.

## Protected holds and reclaim

Immediate approved reclaim: **0 bytes**. Conditional reclaimable unique bytes remain unknown.
The earlier approximately 1.08 GiB proposal is a review candidate, not a verified deletion budget.
The exact 53-item post-check manifest retains source and all Core run evidence and holds the other
paths. It deliberately does not count Python caches again within parent worktrees.

Protected inputs include `PI_M4B_PRODUCTS/8279e79/runtime`, all of
`PI_M4B_ARTIFACTS/60cb29d`, the contained selected-profile worktree, accepted execution worktree,
all result/closure records, manifests, locks, notices and sole reproducibility copies. The shared
cache and Core/Audio material remain outside cleanup authority. Untracked historical worktree
content is not proven rebuildable merely because tracked Git source is reachable.

No scoped live process references were observed, but three same-user processes exited or were
inaccessible, and persistent service/config/rollback references were not comprehensively audited.
This does not establish absence of references or clear any hold.

## Phase 3 plan only

After Core returns a verified canonical product/workspace receipt, update runner-owned identity
and path handling in `run_mva.py`, `mva_identity.py`, `mva_controller.py` and
`mva_litert_backend.py`; do not change these locked files in Phase 1. Bind immutable model,
wheel/native runtime and install-generation identities. Cache keys must include model digest/size,
runtime digest/API revision, device ABI, delegate/backend settings and cache-format revision.
Keep per-run outputs separate; never duplicate model/cache into each run directory. Test receipt
and digest mismatch rejection, mutable/scratch-path rejection, active/rollback isolation, cleanup
safety and absence of per-run large-input copies. Warm-cache timing still requires the measurement
contract's explicit semantics. No canonical path is invented or activated here.

## Validation and remaining work

Completed: three curation tests pass; generated indexes parse; 53-item, 11-worktree, 36-run and
438-evidence-file cardinalities checked; every regular run file hashed; post-check privacy scan
finds no operator-home path or SSH hostname; `git diff --check` passes. MVA surface verification
still passes at `5a1c2ba19908c632bfeb1cd9d0e8f48beaa95e3563c470adcde8be750c95b5ca`.

Unfinished items, explicitly not closed by this packet:

1. Historical attempt 005's exact result and retained sanitized locator remain unknown; never
   reconstruct missing historical raw evidence.
2. Finish coverage of root-level files/shared-cache ownership if needed for any later removal;
   archive and checksum unreproducible untracked/ignored contents before proposing their disposal.
3. Core review/acceptance and authorized commit/push/relay of the sanitized curation set.
   No such publication occurred. The governing income remains unresolved and unarchived.
4. Core Phase 2 workspace receipt is verified; Phase 3 rebinding/tests remain pending and must stay
   inside the assigned roots.
5. Review expired worktree metadata retirement; all real data and metadata remain retained now.
6. Fresh reference/sole-copy checks, exact removal review and explicit User purge authorization.
7. Separate MVA work remains open: unpublished workstation snapshot, Linux/Pi runtime proof and
   measurements, manual semantics, exact Accepted Audio/evidence scope, User publication review,
   and Designer acceptance/gate release. SSH curation authority does not authorize these actions.

## Uncommitted working-set accounting

Base is the full local SHA above, not the Pi SHA. Existing owner edits are preserved. At handoff,
the uncommitted tracked/untracked set comprises:

- `docs/DOCUMENT_INDEX.md`
- `docs/milestone/README.md`
- `docs/pm_handoff/REQUEST-POC-LLM-PI-STORAGE-CURATION-001.md` (incoming owner edit, not edited here)
- `docs/response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md`
- `docs/response/ACK-POC-LLM-PI-STORAGE-CURATION-001.md`
- `docs/response/ACK-LLM-PI-CANONICAL-WORKSPACE-RECEIPT-001.md`
- `docs/response/HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001.md` (concurrent, preserved)
- `docs/delivery/DELIVERY-LLM-PI-CURATION-POSTCHECK-001.md`
- `poc_llm/curation/selected-profile-locators-v1.json`
- `poc_llm/curation/pi-storage-worktree-inventory-v1.json` (concurrent, preserved)
- `poc_llm/curation/pi-cleanup-manifest-v1.json` (concurrent, preserved)
- `poc_llm/curation/llm-result-index-v1.json` (concurrent, preserved)
- `poc_llm/curation/pi-storage-postcheck-v1.json`
- `poc_llm/curation/pi-cleanup-postcheck-v1.json`
- `poc_llm/tools/collect_llm_storage_inventory.py`
- `poc_llm/tools/prepare_curation_postcheck.py`
- `poc_llm/tests/curation/test_storage_inventory.py`

The ignored workstation context is local-only and must not be staged. Before any round-closing
commit, audit every direct incoming handoff and archive only completed/superseded items without
editing their content; this packet performs no round-closing commit.
