# REQUEST-POC-AUDIO-PI-STORAGE-CURATION-001

- Date: 2026-09-06
- From: Core
- Intended owner: Audio POC Team
- Status: PHASE 1 RECEIVED — PHASE 2 WORKSPACE PROVISIONED / CLEANUP NOT AUTHORIZED
- Governing design: Core `docs/arch_pi_directory.md`; applicable storage and
  evidence requirements are restated below for cross-repository intake.
- Product baseline hold: `audio_m4` / `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`

## User authorization for this task

On 2026-09-06 the User directed the Audio POC Team to take this delivery from its
workstation worktree, connect to the Pi, and organize the Audio-owned data. This
authorizes SSH inventory, checksum/index generation, evidence curation, and
non-destructive staging within the paths named below. It does not authorize a new
benchmark, reboot, result publication, commit/push, milestone change, Core checkout
edit, or permanent purge. Those actions retain their existing workflow gates.

This is Phase 1. When the deliverables below are ready, return them to Core and stop.
Do not create `$HOME/snowboard-agent-dev`, a bare repository, new Pi worktrees,
`/opt/snowboard`, `/etc/snowboard`, `/var/lib/snowboard`, service accounts,
permissions, or activation pointers. Core owns that Phase 2 provisioning and will
return a workspace receipt before Audio begins Phase 3 work on the new layout.

## Purpose

Curate the Audio POC's durable source and evidence before the Pi workspace is
migrated and historical test payloads are reclaimed. The most important output is a
reviewable index of prior measurements, including error-rate reports and failed
experiments, so that no result remains discoverable only inside a multi-hundred-MiB
session tree.

This is storage and evidence maintenance. It does not reopen an accepted milestone,
rewrite a submitted SHA, change machine outcomes, start a new research gate, or make
a Core product acceptance claim. Current ALPHA.R1 research inputs remain available
where they contribute to the active outcome contract.

## Protected inputs

Until Core switches to a verified canonical deployment, do not move or remove the
currently referenced M4A product under
`$HOME/m4a-test-runs/6c3ba95-20260829-dev01/product`. Preserve the accepted Audio
Git SHA/tag, all signed/accepted manifests, licenses/notices, checksum locks, the
only copy of any reproducibility input, and every uncurated measurement outcome.

Do not clean the Pi Core checkout or alter another repository. Do not rewrite or
discard rejected-candidate history. Raw/private audio and transcripts must follow
the existing Audio privacy rules and must not be copied into Git for this task.

## Required work

1. Establish the authoritative `audio` branch worktree and record its remote, full
   SHA, tag state, and cleanliness. Classify detached and historical worktrees; use
   standard `git worktree` commands for later retirement.
2. Inventory the following roots by logical owner, unique bytes, reproducibility,
   active references, and evidence value:
   - `$HOME/workspace/poc_audio`;
   - `$HOME/.local/share/audio-poc`;
   - `$HOME/.local/share/sbd` Audio runtime closure;
   - `$HOME/m4a-test-runs`;
   - Audio-related caches and venvs outside those roots.
3. Find and classify every durable metric/result, including WER, CER, error-rate or
   error-category reports, P9/P9.1 results, latency/resource measurements, candidate
   comparisons, M2A/M2B/M3/M4 summaries, formal cards, manifests, checksums, and
   failure reports. Search by content as well as filename.
4. Create a committed sanitized evidence index in the Audio POC repository. Each
   row records result ID, milestone/gate, outcome (`PASS`, `FAIL`, or
   `INCONCLUSIVE` where applicable), Git SHA, candidate/artifact/config identities,
   metric names and values, retained locator, reproduction locator, privacy
   disposition, and source run. Preserve original machine outcomes.
5. Move small authoritative reports into the repository's governed evidence/docs
   locations when policy permits. For large or private material, retain only the
   sanitized aggregate/index and controlled locator required for reproduction.
6. Produce a machine-readable cleanup manifest with one row per candidate path:
   original path, owner, apparent and unique bytes, category (`retain`, `archive`,
   `rebuildable`, `quarantine`, `hold`), reason, active references, retained evidence
   locator/hash, reacquisition/rebuild proof, and proposed expiry.
7. Identify the runner/storage changes needed in Phase 3 to stop per-run
   model/runtime/venv duplication. Record the proposed files and tests in the report;
   do not bind them to paths Core has not provisioned.

The intake audit found at least 44 copies of `model-steps-3.onnx` (3.33 GB), nine
copies of `ggml-base-q8_0.bin` (736 MB), ten copies of
`vocos-16khz-univ.onnx` (539 MB), and five ONNX Runtime wheels (104 MB).
Representative hashes match, but the team must hash every proposed duplicate before
classifying it. These four groups have an estimated maximum reclaim of 4.48 GB; this
is not a deletion grant or a unique-byte guarantee.

The evidence index must explicitly cover the accepted M4 P9.1 and combined 20/20
results at `8be3bc095b504b8eab1dfeb21b94173728b9656f`, the accepted
failure/recovery 12/12 result at `26f33a3c371eee61df46924432839d0fa9ee3bf8`,
and the rejected `79185f992dd1510a9e8298242cec66b237081c52`,
`b7b25ffcd964602531ff1f86ecaa218169f18972`,
`d36490f62679f50a3c109c4a10e80f7ee45221ad`,
`ffcfaa85c9db98333b5ec879f22515bf870b19d1`, and M4-failure
`8be3bc095b504b8eab1dfeb21b94173728b9656f` histories. For `d36490f`, the
governing disposition must state
that the sampler evidence was rejected even though its local `result.json` says
`PASS`.

The accepted result payload hashes observed during intake are
`3f1013c7dfcdc50f92a03441c76d887003927598cb21ebedcac5f9f9f5f2b923`
(P9.1), `4e5fdcdda45a6baac252b47f1ba72aadc4e546034788ca0a180afe4bcbf4d962`
(combined), and
`79360c05f514311ce042057759a9d2a4c23c9a4a890a133bf5fa92cea497c115`
(failure/recovery). The team must resolve these to exact source paths and verify
them again rather than treating this request as the evidence source.

The error-rate section must preserve the current CER and sentence-correctness
reports, including `M4A-M2A-COMPARATIVE-SCORECARD-001.md`,
`M2B-C-PUBLIC-SCORECARD-001.md`, `M4A-M2A-AB-SPLIT-001/summary.json`, and
`M4-ASR-SEMANTIC-PATTERNS-001.md`. It must retain the six-row M2A comparison and the
M2B primary/fallback and prompt-regression conclusions without reinterpreting them.

## Required deliverables

- a committed Audio evidence/result index with a clear section for error-rate and
  candidate-comparison history;
- a committed storage inventory and exact cleanup manifest;
- a Phase 3 runner/storage change plan to stop per-run duplication;
- a return handoff giving the full 40-character Audio SHA when committed, or the
  base SHA and exact uncommitted file list otherwise; changed files,
  validation, protected holds, proposed reclaim bytes, and every unfinished item.

The cleanup manifest must separate apparent size from reclaimable unique bytes. A
directory containing hardlinks, the only artifact copy, an active config target, a
dirty worktree, or unextracted evidence cannot be marked reclaimable.

Known holds include the four uncommitted files in
`m4a-test-runs/telemetry-wt-20260829-d01/repo`, the M4A tester bundle's dependency on
the `6c3ba95-20260829-dev01` repo/config/controller/product, and controlled audio,
transcripts, or User comments whose retention has not been decided.

## Acceptance and deletion boundary

Core accepts this curation when an independent reader can find the accepted and
failed Audio results without retaining bulky run trees, reproduce retained claims
from immutable identities, and see an exact path-level cleanup proposal.

The team may create indexes, copy small sanitized evidence, and stage proposed
removals inside its current owned roots. Runner path changes and canonical migration
wait for Core's workspace receipt. Permanent deletion of historical data is outside
this delivery step until the exact manifest has been reviewed, the canonical M4A
product is deployed, references are rechecked, and the User approves the purge.
Candidate SHAs and accepted tags remain append-only and immutable.
