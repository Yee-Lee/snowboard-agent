# RETURN-POC-AUDIO-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: Audio POC Team
- To: Core
- Requests: `REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001`, `REQUEST-POC-AUDIO-PI-MIGRATION-PUBLISH-001`
- Status: `CORE OUTCOME RECONCILED / PUBLICATION AUTHORIZED`
- Base SHA: `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`
- Phase 1/2/3 commit: `8e0484249ae0756d95151c4a12a1c1b1cdfaee6a`

## Phase 3 source result

The existing append-only commit contains the intended 25-file change set. Formal
execution binds distinct run, evidence, cache, and complete read-only product
roots; hashes the actual product manifest and every formal dependency; rejects
symlinks, writable entries, nested roots, run/cache dependencies, and inventory
mismatch; and no longer consumes installer archives or wheels. The private
exporter streams verified owner-only bundles without staging another Pi archive.

Affected regression is 42/42. Full discovery ran 242 tests: 235 passed; six
workstation-only errors require NumPy and one requires Linux `/proc`. Core's
privacy/downloader suite passed 11/11. Shell syntax, JSON parsing, Python compile,
Git whitespace, and the focused Core privacy gate passed.

## Core receipt reconciliation

Core receipt `RECEIPT-PI-MIGRATION-001` verifies these Audio archives outside all
Git worktrees:

| Bundle | Bytes | SHA-256 | Entries |
| --- | ---: | --- | ---: |
| `audio-phase1-private-001` | 21,574 | `fb6b4080570aa04145ece41331bd7ae4acd97a76a3008cd281ba852ecd23923c` | 10 |
| `audio-phase1-private-incremental-002` | 17,888,533 | `2ecbae3cf5402618013f43f40feb6732441feb11c660d50dbd585988634f4fe8` | 936 |
| `audio-phase1-private-incremental-003` | 192,196,504 | `270f611356ba2436642b9c86e86df445139d1c5f43f14e16bba1ffad93e16fcb` | 269 |

All passed safe-name, regular-file, manifest, per-entry checksum, full coverage,
and archive checksum verification. Pi export trees are cleared; no private
payload entered Git.

`PI_PROD_PRODUCTS/m4a/current` resolves to `audio_m4-5694ead4-v2`. Product manifest
SHA-256 is `3325c5a7cb40634d60c1ab58ef75a0ff3e0008bf12dc15b5a98ba2189c1c69cb`.
The product verifier passed 10,876 dependencies, zero symlinks, zero writable
entries, zero ownership mismatches, and zero legacy shared inodes. Both private
evidence and product-contract change requests are resolved by this receipt.

## Cleanup outcome

Core removed all eight approved Audio work/scratch roots, reclaiming
2,214,473,728 allocated bytes; eight archived result sources; all Audio export
trees and historical evidence/session payloads; old runtime/product inputs; and
all approved non-telemetry legacy M4A runs. The old Audio checkout is retained as
clean Git/source-only history. Final filesystem use is 53% with 27 GiB available.

Read-only post-migration inspection confirmed the canonical product pointer,
empty shared Audio export area, only the intentionally held dirty telemetry M4A
run under the legacy M4A run root, and the clean retained historical checkout.
Five small legacy Audio authorization records remain outside that checkout and
were not named as removal targets; they remain an exact Core-classification hold,
not an implicit purge target.

## Reconciliation commit proposal

Title:

`[docs][M4]: reconcile Pi migration receipts`

Body:

- Record verified private archives and canonical Audio product.
- Reconcile completed cleanup and remaining exact holds.

Files:

- `docs/pm_handoff/REQUEST-POC-AUDIO-PI-MIGRATION-PUBLISH-001.md`
- `docs/pm_handoff/RECEIPT-PI-MIGRATION-001.md`
- `poc_audio/deliveries/RETURN-POC-AUDIO-PI-STORAGE-PHASE3-001.md`
- `poc_audio/manifests/pi_storage_phase3_migration_001.json`
- `poc_audio/manifests/pi_storage_post_download_cleanup_001.json`

After publication, the authorized final operator step is to fast-forward the Pi
canonical Audio worktree to the exact pushed head so the temporary exporter
becomes tracked, verify a clean worktree, and leave `audio_m4` unchanged. Dirty
telemetry, retained historical Git sources, the five unclassified authorization
records, and shared/unknown-owner roots remain outside Audio cleanup authority.
