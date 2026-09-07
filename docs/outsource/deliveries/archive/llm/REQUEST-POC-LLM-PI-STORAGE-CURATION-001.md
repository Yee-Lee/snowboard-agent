# REQUEST-POC-LLM-PI-STORAGE-CURATION-001

- Date: 2026-09-06
- From: Core
- Intended owner: LLM POC Team
- Status: PHASE 1 RECEIVED — PHASE 2 WORKSPACE PROVISIONED / CLEANUP NOT AUTHORIZED
- Governing design: Core `docs/arch_pi_directory.md`; applicable storage and
  evidence requirements are restated below for cross-repository intake.
- Accepted winner input: Gemma 4 E2B mobile / `POC-llm-DEL-2026-001-R3`

## User authorization for this task

On 2026-09-06 the User directed the LLM POC Team to take this delivery from its
workstation worktree, connect to the Pi, and organize the LLM-owned data. This
authorizes SSH inventory, checksum/index generation, evidence curation, and
non-destructive staging within the paths named below. It does not authorize a new
benchmark, reboot, result publication, commit/push, milestone change, Core checkout
edit, or permanent purge. Those actions retain their existing workflow gates.

This is Phase 1. When the deliverables below are ready, return them to Core and stop.
Do not create `$HOME/snowboard-agent-dev`, a bare repository, new Pi worktrees,
`/opt/snowboard`, `/etc/snowboard`, `/var/lib/snowboard`, service accounts,
permissions, or activation pointers. Core owns that Phase 2 provisioning and will
return a workspace receipt before LLM begins Phase 3 work on the new layout.

## Purpose

Curate the LLM POC's authoritative source, selected profile, evidence, and
reproducibility inputs so the real Pi deployment no longer depends on a historical
`gate2b-contained-*` worktree. Classify obsolete worktrees, duplicate runtimes,
large model/cache inputs, and run results before space is reclaimed.

This task preserves the accepted Gate 2B winner and all original machine outcomes.
It does not rewrite an accepted/submitted SHA, change a `FAIL`, start or complete the
M4B-MVA measurement request, or claim Core Gate 3 acceptance.

## Protected inputs

Until Core switches to a verified canonical deployment, do not move or remove:

- `$HOME/m4b-products/8279e79/runtime`;
- `$HOME/m4b-artifacts/60cb29d`;
- the exact selected product profile currently read from
  `gate2b-contained-00e6ae1`;
- accepted closure/publication manifests, exact profile/schema inputs, locks,
  licenses/notices, or the only reproducibility copy of any result.

Do not clean the Pi Core checkout or alter Audio POC material. Private prompts,
responses, and sensitive inputs must not be copied into Git.

## Required work

1. Establish the authoritative `llm` branch worktree and record its remote, full
   SHA, accepted closure/publication ancestry, tag state, and cleanliness. Classify
   every `gate2b-*` worktree as authoritative, historical evidence, rebuildable, or
   hold.
2. Inventory `$HOME/workspace/poc_llm`, `$HOME/m4b-products`,
   `$HOME/m4b-artifacts`, `$HOME/m4b-test-runs`, and related cache/venv locations by
   logical owner, unique bytes, active references, reproducibility, and evidence
   value.
3. Confirm the selected product profile and required schemas exist in a stable,
   tracked location on the accepted LLM lineage. Record their exact SHA-256 values.
   If the accepted lineage does not contain a stable copy, add one in a new
   append-only curation commit without changing the bytes or accepted history.
4. Create a committed sanitized result index covering accepted, failed, waived, and
   inconclusive LLM outcomes; include candidate/profile/model/runtime identities,
   Gate 1/2A/2B results, semantic/resource measurements, retained locators, and
   reproduction metadata. Preserve all original machine values and waivers.
5. Produce a machine-readable cleanup manifest with original path, owner, apparent
   and unique bytes, category (`retain`, `archive`, `rebuildable`, `quarantine`,
   `hold`), reason, active references, retained evidence locator/hash,
   reacquisition/rebuild proof, and proposed expiry.
6. Identify the Phase 3 runner changes needed to reference one content-addressed
   model and immutable runtime product. Record the proposed files, cache identity,
   and tests in the report; do not bind them to paths Core has not provisioned.
7. Provide Core the tracked selected profile/schema locators and hashes needed to
   build `/var/lib/snowboard/products/m4b/<product-id>` without any dependency on a
   mutable or scratch POC worktree.

The intake audit found 11 detached `gate2b-*` worktrees, all clean for tracked
content and reachable from `origin/llm`; about 5.2 MiB of their contents is
`__pycache__`. It also found three separate 147,920 KiB runtime installs with
matching lock/runtime-manifest hashes but distinct inodes, plus a 788,412,736-byte
XNNPACK cache. The model is 2,588,147,712 bytes and the locked wheel is 46,085,754
bytes. The estimated maximum reclaim from one derived cache, two duplicate runtimes,
old worktrees, and Python caches is about 1.08 GiB, subject to active-reference,
benchmark-semantics, and exact-inventory checks.

Pi worktree metadata also contains an expired
`/tmp/llm-poc-g1-src-66ff4b3` entry that appears in `git worktree prune --dry-run`.
Retire it only with the standard Git command after the inventory is recorded. The
36 directories under `m4b-test-runs` require outcome/checksum indexing before any
retention decision; missing historical `/tmp/llm-poc-*` material cannot be inferred
or reconstructed from the Pi.

## Required deliverables

- a committed LLM evidence/result index;
- a committed storage/worktree inventory and exact cleanup manifest;
- stable selected profile/schema locators with checksums;
- a Phase 3 runner/storage change plan to prevent large per-run duplication;
- a return handoff giving the full 40-character LLM SHA when committed, or the base
  SHA and exact uncommitted file list otherwise; changed files,
  validation, protected holds, proposed reclaim bytes, and every unfinished item.

The cleanup manifest must distinguish apparent size from reclaimable unique bytes.
No active target, dirty worktree, sole artifact copy, open evidence question, or
accepted-but-unindexed input is reclaimable.

The workstation `llm` worktree currently contains active M4B-MVA modifications and
untracked source/tests. It is User work and is outside Pi cleanup; do not overwrite,
sync from the Pi, move, or classify it as disposable.

## Acceptance and deletion boundary

Core accepts this curation when a canonical deployment can bind the exact selected
profile/model/runtime without a `gate2b-*` path, historical results remain
discoverable through sanitized committed indexes, and the removal proposal is
path-specific and independently reviewable.

The team may create indexes, copy stable non-sensitive profile/schema inputs, and
stage proposed removals inside its current owned roots. Runner path changes and
canonical migration wait for Core's workspace receipt. Permanent deletion is
outside this delivery step until the exact manifest has been reviewed, the canonical
M4B product is deployed, references are rechecked, and the User approves the purge.
Accepted and submitted SHAs remain immutable; all fixes are append-only.
