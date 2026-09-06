# RECEIPT-PI-PHASE2-WORKSPACES-001

- Date: 2026-09-06
- From: Core
- To: Core, Audio POC, LLM POC
- Status: `PHASE 2 PROVISIONED / NO DEPLOYMENT ACTIVATED / NO CLEANUP AUTHORIZED`
- Governing design: `docs/arch_pi_directory.md`

## Core review

Audio Phase 1 is accepted as sufficient for workspace provisioning. Its 27-result
index, 40-path cleanup manifest, protected holds, and duplicate inventory are still
uncommitted review material. The proposed 2,214,473,728-byte path-level reclaim and
4,499,010,153-byte equal-content estimate overlap and are not deletion authority.

LLM Phase 1 is accepted as sufficient for workspace provisioning. Its worktree/run
inventory and conditional 1,128,083,456-byte estimate are not deletion authority.
The parallel drafts must be reconciled before publication: an earlier ACK still
describes the inventory as not executed, and attempt 005 remains an explicit
evidence gap. All 36 run directories, active products/artifacts, selected-profile
source, accepted evidence, and sole copies remain on hold.

## Development workspace receipt

`PI_DEV_ROOT` is the operator-local `snowboard-agent-dev` directory. The private
absolute mapping is intentionally omitted from Git.

| Owner | Source worktree | Branch | Full SHA | State |
| --- | --- | --- | --- | --- |
| Core | `PI_DEV_ROOT/core` | `core` | `99504776da8bb6dbf753f64775dcb4d0101c02bd` | clean; matches published branch head |
| Audio | `PI_DEV_ROOT/audio` | `audio` | `5694ead4ba6be928fdb4dbdf6da7155b214d72bd` | clean; `audio_m4` peels to this SHA |
| LLM | `PI_DEV_ROOT/poc_llm` | `llm` | `7a56137b7b2d65219ea4ff2065ab2773c179a0af` | clean; published branch head |

The shared bare repository is `PI_DEV_ROOT/.bare`. Its `origin` is
`git@github.com:Yee-Lee/snowboard-agent.git`. It was cloned locally with shared
object hardlinks, then the exact Audio and LLM refs were imported with standard Git
commands. Fetching uses `refs/remotes/origin/*`, so it cannot move a checked-out
local branch. The new Core worktree was fast-forwarded to the published branch after
an ancestry check. The old dirty Core checkout and every historical POC worktree
remain untouched.

Each team may write only to its source worktree and these development data roots:

| Owner | Run output | Evidence export | Reacquirable cache |
| --- | --- | --- | --- |
| Core | `PI_DEV_ROOT/runs/core` | `PI_DEV_ROOT/evidence-export/core` | `PI_DEV_ROOT/cache/core` |
| Audio | `PI_DEV_ROOT/runs/audio` | `PI_DEV_ROOT/evidence-export/audio` | `PI_DEV_ROOT/cache/audio` |
| LLM | `PI_DEV_ROOT/runs/poc_llm` | `PI_DEV_ROOT/evidence-export/poc_llm` | `PI_DEV_ROOT/cache/poc_llm` |

`PI_DEV_ROOT/quarantine` is Core-controlled. Historical roots, another team's data
roots, the old dirty Core checkout, and all Phase 1 holds are forbidden as Phase 3
write or cleanup targets.

## Production boundaries

Core created the empty production boundaries with a dedicated `snowboard` service
account:

- root-owned, group-readable: `/opt/snowboard/releases` and
  `/etc/snowboard/deployments`;
- service-owned: `/var/lib/snowboard/artifacts/sha256`, `products/m4a`,
  `products/m4b`, `runs`, `evidence-export`, `cache`, and `quarantine`;
- service-owned: `/var/log/snowboard` and `/run/snowboard`.

Directories use mode `0750`. No release, product, deployment, configuration, model,
runtime, service unit, or activation symlink was created. Both production `current`
pointers remain absent.

## Space and Phase 3 boundary

The new development tree reports 89,665,536 allocated bytes; filesystem used space
increased by 49,602,560 bytes during provisioning and the final remote-tracking
fetch. The local bare clone shares existing Git objects. Filesystem utilization
remains 78%.

Because utilization is above the 75% high-water mark, teams may make source changes
and small manifests but must not create nonessential benchmarks, model/runtime
copies, new virtual environments, or bulky run output. Phase 3 may begin with path
and installer work against the assigned roots. Moving current dependencies,
materializing a production product, running target validation, activating a
deployment, quarantining old paths, and permanent deletion require their respective
review steps. Permanent purge always requires separate User approval.

## Verification

Core verified the common remote, exact branches and SHAs, annotated milestone tags,
three clean new worktrees, directory ownership/modes, absent activation pointers,
and post-provision disk usage. No Phase 1 hold was moved, modified, or deleted.
