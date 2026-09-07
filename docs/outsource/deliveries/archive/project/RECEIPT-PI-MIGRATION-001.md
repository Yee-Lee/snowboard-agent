# RECEIPT-PI-MIGRATION-001

- Date: 2026-09-06
- Owner: Core
- State: `DEPLOYMENT MATERIALIZED / PRIVATE ARCHIVE VERIFIED / FINAL OWNER TASKS OPEN`

## Canonical deployment

| Team | Current product | Verification |
| --- | --- | --- |
| Audio | `PI_PROD_PRODUCTS/m4a/audio_m4-5694ead4-v2` | PASS; manifest `3325c5a7cb40634d60c1ab58ef75a0ff3e0008bf12dc15b5a98ba2189c1c69cb`; no symlink, writable entry, ownership mismatch, or legacy shared inode |
| LLM | `PI_PROD_PRODUCTS/m4b/8279e79` plus `PI_ARTIFACT_STORE` | PASS; profile/schema/runtime/native/model/wheel fixed identities; independent read-only payloads; no product symlink |

Both `current` pointers resolve to the products in this table. Development
worktrees, mutable runs, temporary evidence export, reacquirable cache, products,
and content-addressed artifacts have separate assigned roots.

## External private archive

| Team | Bundle | Archive bytes | Archive SHA-256 | Entries |
| --- | --- | ---: | --- | ---: |
| Audio | `audio-phase1-private-001` | 21,574 | `fb6b4080570aa04145ece41331bd7ae4acd97a76a3008cd281ba852ecd23923c` | 10 |
| Audio | `audio-phase1-private-incremental-002` | 17,888,533 | `2ecbae3cf5402618013f43f40feb6732441feb11c660d50dbd585988634f4fe8` | 936 |
| Audio | `audio-phase1-private-incremental-003` | 192,196,504 | `270f611356ba2436642b9c86e86df445139d1c5f43f14e16bba1ffad93e16fcb` | 269 |
| LLM | `llm-phase1-m4b-runs-20260906` | 3,290,417 | `a5adfb2bf9b7ad389b2cbdecf076949ddc6fad2adb7c387979923c0509bdd7b5` | 440 |

Core streamed each bundle directly into the private local Pi-download directory,
rejected unsafe/non-regular archive members, verified full checksum coverage and
all payload hashes, verified the complete archive digest, and wrote an atomic
receipt. No private payload entered a Git worktree.

## Cleanup applied

- LLM: 36 archived legacy runs, their export hardlink tree, five approved old
  worktrees, the old product/artifact roots, and the derived accelerator cache.
- Audio: eight work/scratch trees (2,214,473,728 allocated bytes), eight archived
  result sources, the export trees, historical evidence/sessions, the old runtime
  closure and product inputs, and all approved non-telemetry legacy M4A runs.
- Audio development: the stale Pi Audio worktree at `5694ead4` was removed with
  standard `git worktree remove --force` after its only untracked exporter was
  confirmed in the separately retained `8e04842` commit. The M4A canonical
  product remains independent and active.
- The old clean Audio primary checkout was reduced to Git/source-only state by an
  exact dry-run-derived `git clean` path list; it now occupies about 51 MB.
- Preserved: dirty telemetry, clean primary checkouts retained as historical Git
  sources, LLM worktrees containing previously unknown untracked bytes, and
  shared roots without single-team ownership.

The final post-cleanup measurement was 53% used with 27 GiB available. The legacy
Audio primary checkout was about 51 MB, the dirty telemetry root about 28 MB, the
remaining legacy LLM workspace about 30 MB, and the empty old LLM runs root 4 KiB.

## Remaining owner work

- LLM operator: execute the frozen offline M4B-MVA from `ac25aa1` under
  `REQUEST-POC-LLM-M4B-MVA-OFFLINE-EXECUTION-001` and return immutable evidence.
- Audio operator: reconcile actual receipts/cleanup in an append-only commit and
  push `audio` under `REQUEST-POC-AUDIO-PI-MIGRATION-PUBLISH-001`.
- Core: review owner returns, retire only the remaining exact holds whose content
  has been preserved, and close migration status.
