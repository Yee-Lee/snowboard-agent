# Raspberry Pi project directory and storage design

- Status: active target design; Phase 2 roots provisioned; Phase 3 in progress
- Date: 2026-09-06
- Target: Raspberry Pi 5
- Owners: Core owns the layout and deployment boundary; each POC owns its source,
  evidence curation, and cleanup manifest.

## 1. Problem statement

The Pi currently mixes source checkouts, immutable product dependencies, build
inputs, test sessions, virtual environments, caches, and evidence beneath personal
and historical paths. The latest inspected M4B target configuration still loads the
M4A product from `m4a-test-runs/6c3ba95-20260829-dev01`, the LLM runtime from
`m4b-products/8279e79`, the model from `m4b-artifacts/60cb29d`, and the selected
LLM profile from a historical `poc_llm/gate2b-contained-*` worktree. A test-run or
POC cleanup can therefore remove a live dependency.

The 2026-09-06 device snapshot was 44 GiB used of 59 GiB (78%). The largest
relevant roots were `workspace` 9.8 GiB, `.local` 6.1 GiB,
`m4a-test-runs` 3.8 GiB, and `m4b-artifacts` 3.2 GiB. These figures describe the
observed device; they are not retention policy or deletion authorization.

## 2. Design rules

1. A path's purpose determines its root. Source, immutable input, installed
   product, deployment, run output, evidence, cache, and quarantine never share a
   lifecycle boundary.
2. No deployment configuration may depend on `runs/`, `cache/`, `quarantine/`,
   `*-test-runs`, a POC scratch worktree, or another team's mutable checkout.
3. An accepted or deployed identity is immutable. Replacement creates a new
   directory; it never edits an existing product, artifact, deployment, candidate,
   evidence bundle, or accepted Git SHA in place.
4. Git stores source, schemas, small sanitized evidence, manifests, checksums, and
   notices. It does not store models, wheels, native product binaries, virtual
   environments, raw audio, private transcripts, or large raw results.
5. Formal evidence is curated into the owning repository. The shared evidence
   area is only an export/staging surface with a manifest and retention date; it is
   not a second source of truth.
6. Relative YAML paths are resolved from the configuration file directory by the
   existing Core loader. Environment-variable interpolation is not assumed. The
   resolved paths remain absolute at validation time, satisfying the current M4A
   and M4B fail-closed contracts.
7. M4A VAD and TTS runtimes remain isolated product environments. The M4B runtime
   remains an isolated product environment. They must not be merged into the Core
   development venv or into each other.
8. A Git worktree manages source only. Test output and installed dependencies must
   have their own cleanup rules.

## 3. Canonical layout

Development and service deployment are separate planes. A real service never
imports code, locks, profiles, models, or runtimes from a developer worktree. Both
planes may live on the same filesystem, but they have independent ownership and
retention.

On the Pi, the development root is `$HOME/snowboard-agent-dev` so it cannot be
mistaken for the system deployment. A workstation that does not run the production
service may keep the existing `snowboard-agent/` root; renaming it provides no
storage benefit and needlessly invalidates venv and workspace paths.

```text
<development-root>/
├── .bare/                         shared Git object database
├── .git                           optional pointer to .bare for repository commands
├── core/                          persistent worktree, branch core
├── audio/                         persistent worktree, branch audio
├── poc_llm/                       persistent worktree, branch llm
├── runs/                          bounded, disposable execution directories
├── evidence-export/               temporary off-Git transfer bundles
├── cache/                         reacquirable downloads/build caches
└── quarantine/                    staged removals with expiry and manifest
    └── <batch-id>/
        ├── manifest.json
        └── payload/
```

The real deployment uses standard system locations and can run under a dedicated
`snowboard` service account:

```text
/opt/snowboard/
├── releases/<release-id>/          immutable Core application/runtime release
│   ├── app/
│   ├── runtime/
│   └── release.json
└── current -> releases/<release-id>

/etc/snowboard/
├── deployments/<deployment-id>/
│   ├── target-config.yaml
│   ├── deployment.json
│   └── SHA256SUMS
└── current -> deployments/<deployment-id>

/var/lib/snowboard/
├── artifacts/sha256/<first-2>/<digest>/
│   ├── payload
│   └── artifact.json
├── products/
│   ├── m4a/<product-id>/           complete verified M4A install root
│   └── m4b/<product-id>/           verified isolated M4B runtime/profile
├── runs/<component>/<run-id>/      bounded service/acceptance runs
├── evidence-export/<owner>/<id>/   temporary sealed transfers
├── cache/<component>/              reacquirable data only
└── quarantine/<batch-id>/          non-active staged removals

/var/log/snowboard/                 bounded service logs when journald is insufficient
/run/snowboard/                     sockets/PIDs only; cleared at boot
```

`/opt`, `/etc`, and `/var/lib` are logical boundaries, not a reason to duplicate
payloads. On the Pi they currently share the root filesystem. The model and each
installed runtime have one canonical physical copy per retained identity.

The development worktrees may share `.bare` only when their histories and remotes are
the intended common repository. Migration must verify the remote URL, branch, full
HEAD SHA, and worktree cleanliness first. It must not graft unrelated repositories
or rewrite branch history merely to obtain this layout.

## 4. Identity and ownership

| Root | Writer | Required identity | Mutability | Removal condition |
| --- | --- | --- | --- | --- |
| development worktrees | owning Git team | remote, branch/tag, full SHA | normal source workflow; published SHA immutable | `git worktree remove` after clean-state and ownership check |
| `/var/lib/.../artifacts` | provisioning | SHA-256, size, source locator, license/notice | write once, read-only | no product/deployment reference and reacquisition proven |
| `/var/lib/.../products` | product installer | delivery/candidate ID, input hashes, complete inventory | write once, no symlinks | no deployment reference and replacement preflight passed |
| `/opt/.../releases` | release builder | release ID, Core SHA, package inventory | write once | superseded, rollback window expired, no deployment reference |
| `/etc/.../deployments` | Core/operator | deployment ID, release/product IDs, config hash | write once | superseded, evidence captured, rollback window expired |
| `runs` | runner owner | run ID, owner, purpose, start/end/status | mutable until terminal | terminal, evidence extracted, no deployment reference |
| `evidence-export` | evidence owner | bundle ID, source SHA, manifest hash, retention date | append until sealed | committed/received authoritative evidence verified |
| `cache` | component owner | optional cache index | disposable | not in use; reacquisition path exists |
| `quarantine` | operator | original path, reason, owner, size, moved-at, expires-at | payload read-only | expiry reached and owner/user approves final purge |

`artifact.json`, product inventories, deployment manifests, and cleanup manifests
must use logical locators and relative paths. They must not persist `/home/<user>`
or test-session paths.

## 5. Deployment binding

Each `/etc/snowboard/deployments/<id>` directory binds one Core release to exact
product inputs. A
deployment manifest must record at least:

- schema version and deployment ID;
- Core full SHA and branch/tag context;
- M4A product ID, accepted Audio SHA, install-inventory digest, and lock digest;
- M4B product ID, runtime inventory digest, model digest, profile digest, and lock
  digest;
- target-config digest, creation time, creator role, target hostname/platform;
- preflight command versions and sanitized PASS/FAIL results;
- predecessor deployment and rollback deadline.

Production YAML uses stable, user-independent absolute paths below
`/opt/snowboard` and `/var/lib/snowboard`. Development and test YAML may use paths
relative to the YAML directory; the loader resolves them before strict validation.
No YAML interpolation feature is required. The `current` symlinks are for service
activation and operator discovery; product preflight receives resolved physical
deployment, release, and product paths.

The M4A product remains a complete verified install root containing the Whisper
worker/model, Silero model/runtime, Matcha model, Vocos model, and isolated VAD/TTS
runtimes. The shared artifact store holds reacquirable build inputs and large
immutable inputs; it does not replace the M4A install inventory. The M4B product
owns its isolated runtime and selected profile copy; the large model may remain a
content-addressed artifact referenced by exact digest. Once an M4A product is
installed and verified, reacquirable source payloads duplicated in `artifacts` may
be garbage-collected; the installed product is the single active physical copy.
For M4B, the large model stays in `artifacts` and is not copied into the runtime
product. A generated XNNPACK cache is keyed by model/runtime/device-profile digest;
only the active and rollback identities are retained.

## 5.1 Space budget and release retention

The device must reserve the greater of 10 GiB or 20% filesystem capacity as normal
free headroom. At 75% use, automated creation of nonessential review/scratch copies
stops; at 85%, only bounded recovery and evidence extraction may write until an
operator clears space.

Before staging a release, available space must cover the new unique bytes, the
active release, one rollback release, the expected run bound, and 2 GiB emergency
headroom. A release switch retains exactly the active deployment and one known-good
rollback by default. Older releases/products become garbage-collection candidates
only after the reference graph is recomputed.

Space-saving rules are:

- content-address each large payload and keep one physical copy per retained hash;
- do not snapshot venvs/models into every run; runs reference immutable products;
- retain one current generated accelerator cache per active/rollback identity;
- delete a downloaded wheel/archive after verified installation when it is
  reacquirable and offline rollback does not require it;
- never duplicate formal evidence in both a POC run tree and Core Git after receipt;
- use hardlinks only as a recorded migration technique for immutable same-filesystem
  files; normal operation must not rely on mutable hardlinked products;
- measure unique bytes, not directory apparent size, before claiming savings.

## 6. Evidence policy

The owning repository is authoritative for small, sanitized, reviewable evidence:

- Audio POC owns candidate comparison, WER/CER or other error-rate summaries,
  latency/resource summaries, failed-path conclusions, accepted delivery indexes,
  and their reproduction metadata.
- LLM POC owns selected profile/schema, semantic and performance summaries,
  failed-path conclusions, accepted delivery indexes, and reproduction metadata.
- Core owns product-delta evidence and exact-Core-SHA acceptance evidence under
  `docs/outsource/evidence/`.

Raw sessions are not evidence merely because they exist. Before a run becomes
eligible for cleanup, its owner must produce an evidence extraction record listing
the run ID, Git SHA, artifact/config hashes, commands or runner version, sanitized
metrics, outcome, retained locators, omitted private data, and the checksum of the
sealed record. Failed and rejected results are retained in the curated index; bulky
runtime/model copies may then be removed without rewriting the historical outcome.

Private audio, transcripts, prompts, and model responses must not be moved into Git
or shared evidence exports. Their retention and destruction follow the owning POC's
privacy rules. A metric report may retain aggregate counts and error categories only
when they cannot reconstruct private content.

Private bundle packaging and the staged Git check follow
[`runbooks/private_evidence.md`](runbooks/private_evidence.md). Public documents may
identify `Yee.Lee` and `yeelee.tw@gmail.com`; they must omit workstation type/OS,
private home paths, local host identities, raw content, and operator-specific paths.

## 7. Run and cache retention

Every new run starts with a machine-readable `run.json` containing owner, purpose,
Git SHA, input identities, expected outputs, retention class, and expiry. At normal
or failed termination, the runner records terminal status and cleanup completion.

Default classes are:

| Class | Examples | Default retention |
| --- | --- | --- |
| `scratch` | local probes, interrupted setup, regenerated venv | 3 days after terminal state |
| `development` | ordinary candidate iteration | 14 days after evidence extraction |
| `review` | submitted/rejected candidate raw run | 30 days after review and extraction |
| `formal-export` | sealed transfer awaiting receipt | until receipt verification, then 14 days |
| `hold` | unresolved incident, only copy, legal/license question | no automatic expiry |

Age alone never authorizes deletion. A cleanup candidate must also be terminal,
unreferenced by products/deployments, have evidence extracted where required, and
not be on hold. Cache cleanup requires a documented reacquisition source or build
recipe.

## 8. Migration sequence

Migration has three owner-separated phases. A phase does not begin until the prior
owner has returned its receipt.

### Phase 1 — POC teams curate the existing Pi

1. **Freeze destructive cleanup.** Record disk state, running processes, mounts,
   Git remotes/worktrees/status, and all configured paths. Preserve the currently
   referenced M4A/M4B/product-profile paths and the dirty Pi Core worktree.
2. **POC curation.** Audio and LLM produce reviewable evidence indexes and cleanup
   manifests. Commit and publication follow each repository's approval workflow.
   Audio must specifically recover historical error-rate and candidate comparison
   reports before any session directory is retired.

Each POC returns a report containing its base/result SHA, changed files, evidence
index, exact cleanup manifest, protected holds, expected unique-byte reclaim, and
unfinished items. It then stops. POC teams must not create the canonical development
root, system deployment roots, worktrees, permissions, service account, or `current`
pointers during Phase 1.

### Phase 2 — Core provisions the Pi

3. **Provision the target roots.** Core creates `$HOME/snowboard-agent-dev`, the
   shared bare repository, `core`, `audio`, and `poc_llm` worktrees, and the `/opt`,
   `/etc`, `/var/lib`, `/var/log`, and `/run` boundaries with explicit ownership and
   documented high-water limits. Core does not move current dependencies yet.
4. **Issue workspace receipts.** For each team, Core records the physical path,
   remote, branch, full SHA, cleanliness, writable data roots, quota/high-water
   limit, and forbidden roots. Audio/LLM work does not resume until it receives this
   receipt.

### Phase 3 — Teams populate and use the provisioned workspace

5. **Materialize immutable inputs/products.** The owning team works only inside its
   assigned roots. Verify source and destination size and
   SHA-256. Use the existing product installers and inventories. Temporary hardlinks
   are allowed only for verified immutable large files on the same filesystem and
   must be recorded; no symlink may enter a product tree.
6. **Create a new deployment.** Core generates production YAML and the deployment manifest.
   Run strict config loading plus M4A and M4B product preflights against physical
   paths.
7. **Validate on target.** Run bounded smoke/diagnostic checks, confirm cleanup, and
   confirm logs/results contain no private paths or content. This migration does not
   claim a milestone PASS unless the formal Tester process says so.
8. **Switch atomically.** Change only the operator `current` pointer after the new
   deployment passes. Keep the predecessor intact through the rollback window.
9. **Quarantine old material.** Move approved unreferenced candidates into a named
   quarantine batch with a manifest. Use `git worktree remove` for registered
   worktrees. Never delete or edit Git internals directly.
10. **Purge after review.** Recheck references, checksums, free space, and POC/Core
   receipts. Final deletion uses the exact quarantine manifest and records recovered
   bytes.

## 9. Migration gates

Migration is ready to switch only when all of the following are true:

- no canonical deployment path contains `*-test-runs`, `/tmp`, a scratch worktree,
  or a mutable POC checkout;
- all deployed files exist and match the tracked locks/inventories;
- strict `load_config()` and both product preflights pass from the new physical
  paths;
- the selected LLM profile no longer comes from `gate2b-contained-*`;
- the M4A runtime no longer comes from a historical test run;
- Audio and LLM evidence indexes identify accepted, rejected, and inconclusive
  outcomes without depending on bulky run directories;
- the old deployment remains recoverable until rollback expiry;
- the cleanup manifest has no dirty worktree, active process, open file, sole
  artifact copy, unresolved evidence, or hold item.

## 10. Current device holds

The following observed locations are protected until a replacement deployment has
passed the gates above:

- `m4a-test-runs/6c3ba95-20260829-dev01/product` (current M4A runtime/assets);
- `m4b-products/8279e79/runtime` (current M4B runtime);
- `m4b-artifacts/60cb29d` (selected model, cache, and wheel);
- `workspace/poc_llm/gate2b-contained-00e6ae1/...CAND-LRT-...json`
  (currently selected profile);
- `workspace/snowboard-agent` because its Core checkout has local modifications;
- any Audio/LLM run containing the only uncurated metric or error-rate evidence.

No directory in this section is a cleanup candidate merely because another copy
appears to exist.
