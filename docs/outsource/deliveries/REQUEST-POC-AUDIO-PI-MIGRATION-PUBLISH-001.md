# REQUEST-POC-AUDIO-PI-MIGRATION-PUBLISH-001

- Date: 2026-09-06
- From: Core
- Owner: Audio operator CLI
- Status: `AUTHORIZED — RECONCILE AND PUSH`
- Existing append-only commit: `8e0484249ae0756d95151c4a12a1c1b1cdfaee6a`

## User direction

The User assigned Audio's final commit and push to the separate Audio operator
CLI. Do not amend the existing commit or move `audio_m4`. Reconcile the final Pi
receipts and cleanup as a new append-only commit, then push the `audio` branch to
the existing `origin/audio` destination.

## Core receipts to record

| Bundle | Archive bytes | Archive SHA-256 | Entries |
| --- | ---: | --- | ---: |
| `audio-phase1-private-001` | 21,574 | `fb6b4080570aa04145ece41331bd7ae4acd97a76a3008cd281ba852ecd23923c` | 10 |
| `audio-phase1-private-incremental-002` | 17,888,533 | `2ecbae3cf5402618013f43f40feb6732441feb11c660d50dbd585988634f4fe8` | 936 |
| `audio-phase1-private-incremental-003` | 192,196,504 | `270f611356ba2436642b9c86e86df445139d1c5f43f14e16bba1ffad93e16fcb` | 269 |

All three archives passed Core's safe-name, regular-file, manifest, per-entry
SHA-256, and archive SHA-256 verification and are stored in the local private
Pi-download directory outside every Git worktree. Their Pi export trees have
been cleared.

## Accepted product and cleanup state

- `PI_PROD_PRODUCTS/m4a/current` resolves to
  `audio_m4-5694ead4-v2`.
- Product manifest SHA-256 is
  `3325c5a7cb40634d60c1ab58ef75a0ff3e0008bf12dc15b5a98ba2189c1c69cb`.
- The verifier passed 10,876 dependencies, zero symlinks, zero writable entries,
  zero owner/group mismatches, and zero legacy shared inodes.
- Core removed the eight approved work/scratch trees (2,214,473,728 allocated
  bytes), their eight archived source-result files, the old sessions/evidence,
  old runtime/product inputs, and every non-telemetry legacy M4A run listed by
  Audio after all three receipts passed.
- The dirty telemetry worktree remains held. The old clean primary checkout
  remains for a separate exact cleanup because broad `git clean` was rejected.

## Required publication

1. Re-read Audio's workflow and verify that `8e0484249ae0756d95151c4a12a1c1b1cdfaee6a`
   contains the intended 25-file Phase 1/2/3 change set.
2. Update the return, cleanup manifest, and migration status with the three Core
   receipts and the actual cleanup outcome. Remove stale claims that download,
   materialization, activation, or cleanup are still waiting.
3. Keep physical host/home paths and private payload details out of Git; run the
   focused privacy gate and `git diff --check`.
4. Create one append-only reconciliation commit with a full proposal, then push
   both commits by pushing `audio` to the existing `origin/audio` remote. Report
   the two final SHAs and remote ref.
5. The stale Pi Audio worktree was removed at the User's direction after its
   untracked exporter was confirmed present in `8e04842`. Do not recreate it as
   part of publication. If later Pi development is required, create a fresh
   worktree from the shared bare repository at the pushed `audio` head. Do not
   move `audio_m4`.
