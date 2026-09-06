# ACK-POC-LLM-PI-STORAGE-CURATION-001 — Phase 1 local intake (superseded)

- Date: 2026-09-06
- Income: `REQUEST-POC-LLM-PI-STORAGE-CURATION-001`
- Income SHA-256 at intake: `1516e9fc3f67374821c30adb6f70941d9ab5ad2ec5d5bc9884dede607d3247d0`
- Local base SHA: `57390cc1ed7aef7a3a172716bb71e622649c4f67`
- State: `SUPERSEDED HISTORICAL INTAKE / NOT CURRENT EXECUTION STATUS`

This document is the preserved pre-execution intake snapshot. Its statements that Pi inventory was
not executed and Phase 1 was incomplete were superseded by
`HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001` and
`ACK-LLM-PI-CANONICAL-WORKSPACE-RECEIPT-001`. Phase 1 inventory is complete and the Core Phase 2
workspace receipt is now read-only verified. Attempt 005 remains open; no result is inferred.

## Local development checkpoint

MVA WP01 source, tests, packet and surface lock are complete in the local base commit. Its 53
targeted tests pass. Full-suite platform failures reproduce on the unchanged handoff baseline.
Push was rejected by automatic approval review: destination trust and explicit private-payload
export authorization were considered insufficient, even after read-only verification that
`origin/llm` contains the starting `7a56137b7b2d65219ea4ff2065ab2773c179a0af` commit. User then
directed completion locally before handling Core curation; no further push is attempted.

The current income was updated concurrently by its owner. Its latest Phase 1 instructions are
preserved, including the ban on Phase 2 provisioning and deferral of runner path changes to Phase 3.
Those incoming changes and this local intake are left uncommitted. No MVA benchmark, Pi connection,
reboot, path migration, external relay or deletion was performed.

## Verified canonical source locators

The selected profile already exists at a stable tracked path in accepted publication
`485bb2a7c07d86a09899f09358c744edd733f875`. Its bytes and four required schemas match both
historical `00e6ae1401f21dd498a29bba7985ca387130884c` and the local base commit.
No new copy is needed; Core can obtain these files by exact publication SHA and tracked path.
Checksums, model/runtime identity, closure/execution ancestry and the `llm_m4` tag object are in
[`selected-profile-locators-v1.json`](../../poc_llm/curation/selected-profile-locators-v1.json).

The selected product profile is `gate2b-product-v2.json`, digest `c4557b…5171e`, protocol
`snowboard.llm/1`. The newer MVA `text/end` / `snowboard.llm/2` experiment is not an accepted
replacement and must not be substituted during storage curation. Original `/tmp` artifact bindings
inside the accepted profile remain unchanged; Core Phase 2 must define the canonical installation
receipt and explicit rebinding. A stable Git locator does not prove the running Pi currently uses it.

## Phase 1 remaining work

1. Read-only Pi inventory: current authoritative `llm` worktree and all `gate2b-*` worktrees;
   LLM-owned product/artifact/test-run/cache/venv locations; actual references, hard links,
   apparent bytes, allocated/unique bytes and reproducibility copies. Core's 11 worktrees,
   36 run directories and approximately 1.08 GiB estimate remain incoming claims until verified.
2. Build a complete sanitized result index from retained receipts and published source records.
   Preserve PASS/FAIL/INCONCLUSIVE and governance waivers separately, including the accepted Gemma
   P2/P8/P9/P10B machine failures. Unknown/missing historical `/tmp` records remain unknown.
3. Produce the exact cleanup manifest only after inventory. Keep protected runtime/artifact/profile
   inputs, sole copies, dirty/active worktrees and unindexed evidence on hold. No bytes are currently
   declared reclaimable; `null` means unknown, not zero or approved deletion.
4. Prepare a Phase 3 change plan for canonical model/runtime references and cache keys based on
   model/runtime/device identity. Do not create new roots, services, accounts or activation pointers;
   do not change runner paths before Core's workspace receipt.
5. Return a reviewable Phase 1 handoff with base SHA, exact changed-file list, validation and open
   items. New commit/push, external relay and permanent purge retain their separate workflow gates.

The latest direct instruction is being handled as local development first. The earlier MVA
stop-before-Pi boundary is retained for this local checkpoint; the income's delegated Phase 1 Pi
scope is recorded but has not been exercised. No private connection information is inferred from
the previous workstation. Phase 1 is not complete and no milestone state is advanced by this ACK.
