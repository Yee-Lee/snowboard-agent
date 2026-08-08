# Audio POC workstation readiness

Run the environment pre-test before starting development on a new workstation,
before a Pi hardware session, and after a significant OS/audio configuration
change. It is read-only on the Pi: it does not capture audio, play audio,
create remote files, or start a remote process.

## One-time workstation setup

Keep the following on the operator's workstation, outside this repository:

1. An SSH credential approved for the target Pi.
2. A trusted host-key entry verified through an approved secure channel.
3. A local SSH config with an operator-selected alias, account, and key.

Do not put the endpoint, account, credential, key path, host fingerprint, or
connection config in Git. The repository's `.gitignore` excludes local M0
connection config and raw evidence directories as a defence in depth measure.

## Run the pre-test

From the repository root, point `M0_SSH_CONFIG` to the local config and pass
its alias as the first argument:

```sh
M0_SSH_CONFIG=/protected/path/config \
  bash poc_audio/tools/environment_pre_test.sh <operator-alias>
```

To choose a local evidence directory explicitly:

```sh
M0_SSH_CONFIG=/protected/path/config \
  bash poc_audio/tools/environment_pre_test.sh \
  <operator-alias> poc_audio/evidence/m0/<timestamp>-pretest
```

The pre-test returns exit code `0` only when all of the following pass:

- Local commands required by the M0 tools are present.
- Non-interactive SSH access works using the local, operator-managed config.
- The target identifies as Raspberry Pi 5 on `aarch64`.
- The remote commands needed by M0 are present.
- At least one capture and playback device is visible.
- No process currently owns an audio device.

It also records the repository commit SHA/dirty state, OS/kernel, available
disk, temperature, throttling state, and device counts. These facts help
compare later benchmark evidence but are not performance gates themselves.

## Interpret the result

On success, the tool prints the local evidence path and writes:

- `environment.txt` — sanitized readiness inventory.
- `result.txt` — `PASS`.

Those files are intentionally Git-ignored. Review them locally or transfer a
sanitized version through the approved evidence channel; do not add the raw
directory to Git.

On failure, inspect only the generic reason in `result.txt`, correct the local
configuration or Pi condition, then rerun. The tool intentionally suppresses
connection error text from evidence because it can disclose local endpoint
details.

## Before an official M0 evidence bundle

The pre-test confirms environment readiness only. When a new M0 control/evidence
bundle is required, run the separate lifecycle and transfer probe after a
passing pre-test:

```sh
M0_SSH_CONFIG=/protected/path/config \
  bash poc_audio/tools/m0_remote_readiness.sh <operator-alias>
```

That probe creates one short-lived, isolated remote test process and a harmless
temporary marker, then proves timeout/cancel cleanup and checksum-preserving
file transfer. Do not run either tool during a formal latency, resource, or
offline measurement.

## Maintain the Pi checkout

The Pi needs a repository checkout, but it is a **clean deployment/test
worktree**, not a second place to author changes. The Git repository and a full
commit SHA are the source of truth for every hardware result.

Use a feature branch and Draft PR for iterative work. A `wip:` commit is allowed
for a small incomplete change, but do not use a moving branch head as a hardware
baseline: each Pi run must check out and record an exact full SHA. Before a
candidate or milestone gate, create an immutable tag (or retain the POC branch)
for the tested SHA. This preserves reproducibility even if the PR is later
squash-merged.

Recommended flow:

1. Make and review changes on the developer workstation.
2. Commit the intended state locally and make it available through the team's
   approved Git transport.
3. On the Pi checkout, fetch and check out that exact full commit SHA.
4. Confirm `git status --porcelain` is empty, then run `environment_pre_test`.
5. Record the checked-out SHA with every hardware evidence bundle.

Do not make uncommitted fixes directly on the Pi before a benchmark. If an
urgent Pi-only change is necessary, bring it back into the primary repository,
commit it, then repeat the clean-checkout and pre-test sequence.

Use Git for source deployment. Use SCP/rsync only for controlled non-Git
artifacts (such as models or raw evidence) with checksum verification; never
use it to overlay selected source files onto the Pi checkout.
