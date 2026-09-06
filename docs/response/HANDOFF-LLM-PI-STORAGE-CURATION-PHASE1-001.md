# HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001

- Date: 2026-09-06
- Request: `REQUEST-POC-LLM-PI-STORAGE-CURATION-001`
- Owner: LLM POC Team
- State: `PHASE_1_COMPLETE / CORE_PHASE_2_WORKSPACE_RECEIPT_VERIFIED / PHASE_3_PENDING`
- Local base SHA: `57390cc1ed7aef7a3a172716bb71e622649c4f67`
- Commit/push: not performed

## Returned curation set

This Phase 1 return adds the following independent, uncommitted files without changing MVA
source, tests, packet or surface locks:

1. `poc_llm/curation/pi-storage-worktree-inventory-v1.json`
2. `poc_llm/curation/pi-cleanup-manifest-v1.json`
3. `poc_llm/curation/llm-result-index-v1.json`
4. `docs/response/HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001.md`

The concurrently created `poc_llm/curation/selected-profile-locators-v1.json` is consumed as the
stable selected-profile return. It was present before this Pi inventory write and was not
overwritten. Existing local MVA and income edits remain owner work and are outside this return.

The full uncommitted tree observed at final validation is listed below so Core can separate this
return from concurrent work. Only the four uncommitted repository files numbered above were
written by this Phase 1 inventory task.

```text
 M docs/DOCUMENT_INDEX.md
 M docs/milestone/README.md
 M docs/pm_handoff/REQUEST-POC-LLM-PI-STORAGE-CURATION-001.md
 M docs/response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md
?? docs/delivery/DELIVERY-LLM-PI-CURATION-POSTCHECK-001.md
?? docs/response/ACK-POC-LLM-PI-STORAGE-CURATION-001.md
?? docs/response/ACK-LLM-PI-CANONICAL-WORKSPACE-RECEIPT-001.md
?? docs/response/HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001.md
?? poc_llm/curation/llm-result-index-v1.json
?? poc_llm/curation/pi-cleanup-manifest-v1.json
?? poc_llm/curation/pi-cleanup-postcheck-v1.json
?? poc_llm/curation/pi-storage-postcheck-v1.json
?? poc_llm/curation/pi-storage-worktree-inventory-v1.json
?? poc_llm/curation/selected-profile-locators-v1.json
?? poc_llm/tests/curation/test_storage_inventory.py
?? poc_llm/tools/collect_llm_storage_inventory.py
?? poc_llm/tools/prepare_curation_postcheck.py
```

All public files use `PI_LLM_WORKSPACE`, `PI_M4B_PRODUCTS`, `PI_M4B_ARTIFACTS`, `PI_M4B_RUNS`,
`PI_SHARED_CACHE` and `PI_TMP_WORKTREE_METADATA` logical locators. Host, operator-home and
platform fingerprints are omitted. The exact logical-to-real locator mapping was written only to
the mode-0600 Pi-side `PI_PRIVATE_BUNDLE/llm-pi-storage-locators-v1.private.json` outside Git;
its SHA-256 is `bc10368e1eb6cd59bf31e3b3a6aa2cde3eed96ff1b2829da89e18eb4da2069d3`.

## Phase 1 findings

The Pi repository has no worktree attached to the authoritative `llm` branch. Its canonical
checkout is detached at `e2b59fac609e0d768ff3554754363900cbed70a9`; the local `llm` branch is
stale at `afb310b5337857e01741ab455086b53f9904f280`. The Pi remote-tracking ref advanced during
Phase 1 from accepted Gate 2B execution `0c75536e6ee99b502c59438989ca852194648946` to
`7a56137b7b2d65219ea4ff2065ab2773c179a0af`; the final recheck records the latter without changing
any checkout. All 11 `gate2b-*` worktrees are tracked-clean and
their HEADs are reachable from `origin/llm`. Five contain a 51-byte SQLite session side effect,
one contains an empty untracked file, and all contain only rebuildable Python cache among ignored
content. One absent scratch worktree remains as prunable Git metadata. No checkout, new worktree or
prune was performed.

The selected product profile already exists at a stable tracked path on accepted publication
`485bb2a7c07d86a09899f09358c744edd733f875`. Its SHA-256 is
`c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e`; the strict config,
protocol, prompt and response schema digests are returned in the selected-profile locator and
result index. The current worktree dependency on `gate2b-contained-00e6ae1` remains protected
until Core supplies and verifies the Phase 2 canonical binding.

Three runtime installations occupy about 151.47 MB allocated each. Their artifact and runtime
manifest hashes match, while native files have distinct inodes; two are real duplicate
allocations. The selected model is 2,588,147,712 bytes with SHA-256
`181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`; the locked wheel is
46,085,754 bytes with SHA-256
`5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00`. The derived 788,412,736
byte XNNPACK cache has SHA-256
`46179cd630dcea671b46058ef2c017015099174071640afb22b1bd98cba83ab3`. All three remain on hold.

The 36 `PI_M4B_RUNS` directories were indexed with apparent/allocated bytes, file count and a
per-directory tree SHA-256. They are shared Core M4B evidence rather than LLM Gate evidence and
remain protected. The sanitized LLM result index separately preserves Gate 1, Gate 2A and Gate 2B
machine outcomes, including every FAIL/INCONCLUSIVE state and the later governance waivers. It
contains no prompts, responses or raw result copies. Attempt 005 remains explicitly unknown
rather than inferred.

The maximum later reclaim proposal is 1,128,083,456 allocated bytes (1,075.824 MiB): 11 extra
worktrees, two duplicate runtimes, one derived XNNPACK cache and one empty product directory.
Phase 1 reclaimable bytes are zero. This is an estimate for exact path review, not deletion
authorization, and deliberately avoids double-counting Python caches within the worktrees.

## Protected holds

- `PI_M4B_PRODUCTS/8279e79/runtime`;
- `PI_M4B_ARTIFACTS/60cb29d`, including the selected model and locked wheel;
- `PI_LLM_WORKSPACE/gate2b-contained-00e6ae1` until canonical profile rebinding is verified;
- `PI_LLM_WORKSPACE/gate2b-no-psi-0c75536` until accepted execution evidence is independently
  retained;
- all 36 `PI_M4B_RUNS` directories;
- accepted closure/publication manifests, exact profile/schema inputs, locks, licenses/notices and
  any sole result copy;
- `PI_SHARED_CACHE`, whose ownership includes non-LLM material.

No process reference matched the scoped LLM/M4B inputs at inventory time. This point-in-time check
does not clear the holds. Core must recheck running processes, services, target configs and
rollback references immediately before any approved cleanup.

## Phase 3 runner and cache plan

Core Phase 2 first provisions the immutable product and returns its workspace receipt. LLM then
changes only the runner-owned path/identity boundary:

- `poc_llm/tools/run_mva.py`: accept Core-provided immutable model, runtime, wheel and install
  generation locators; record content identities and reject scratch-worktree bindings.
- `poc_llm/harness/mva_identity.py`: authenticate the Core receipt, model/wheel/runtime digests and
  install generation; fail closed if bytes or stat identity change during the run.
- `poc_llm/harness/mva_controller.py`: pass the verified immutable locators to the child and keep
  run output in the per-run result directory only.
- `poc_llm/harness/mva_litert_backend.py`: consume the supplied verified model locator without
  copying the model or shared cache into a run directory.
- corresponding identity/controller/backend/surface tests: reject digest mismatch, mutable or
  `gate2b-*` dependencies and per-run model/cache copies; verify active/rollback cache isolation
  and prove cleanup never removes the shared immutable input.

The content-addressed cache key must include model SHA-256 and size, runtime wheel/native digest,
runtime API/source revision, device ABI, backend/cache format revision and accelerator/delegate
settings. A runner builds into a private temporary output and promotes it only after identity
verification. Whether a warm cache may be used by a timed MVA remains part of the measurement
contract; Phase 1 does not change benchmark semantics.

## Validation and unfinished items

Core subsequently returned its Phase 2 workspace receipt. Read-only verification confirmed
`PI_DEV_ROOT/poc_llm` on clean branch `llm` at
`7a56137b7b2d65219ea4ff2065ab2773c179a0af`, with matching `origin/llm`; the assigned run,
evidence-export and cache roots exist as non-symlink directories with writable access. See
`ACK-LLM-PI-CANONICAL-WORKSPACE-RECEIPT-001`. No root was written and Phase 3 did not start.

Validation covers JSON parsing, 36-run cardinality, worktree cardinality, cleanup-total arithmetic,
SHA-256 format checks for every full digest, whitespace checks and a public-tree scan for private
home paths, hostnames and common credential forms. The final remote read-only recheck at
`2026-09-06T10:49:03+08:00` found 12 live worktrees, one stale metadata record, zero tracked-dirty
entries, and matching protected model/wheel/cache/runtime hashes. No file move, delete, benchmark,
reboot, checkout, commit or push occurred.

Core Phase 2 must provision the canonical product/workspace and return the exact receipt before any
runner edit. Phase 3 must perform the rebinding and cache-key tests. Attempt 005's exact result and
retained locator remain an open evidence question. Permanent deletion requires
review of the exact cleanup manifest, successful canonical deployment, a fresh reference check and
explicit User approval.
