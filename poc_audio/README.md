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
M0_SSH_CONFIG=/protected/path/config PI_POC_REPO=/protected/path/to/pi-worktree \
  bash poc_audio/tools/environment_pre_test.sh <operator-alias>
```

To choose a local evidence directory explicitly:

```sh
M0_SSH_CONFIG=/protected/path/config PI_POC_REPO=/protected/path/to/pi-worktree \
  bash poc_audio/tools/environment_pre_test.sh \
  <operator-alias> poc_audio/evidence/m0/<timestamp>-pretest
```

The pre-test returns exit code `0` only when all of the following pass:

- Local commands required by the M0 tools are present.
- Non-interactive SSH access works using the local, operator-managed config.
- The target identifies as Raspberry Pi 5 on `aarch64`.
- The specified Pi worktree is clean and at exactly the local full commit SHA.
- The remote commands needed by M0 are present.
- At least one capture and playback device is visible.
- No process currently owns an audio device.

It also records the local/Pi repository SHA, Pi worktree dirty-file count, OS/kernel, available
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

## Git/Pi worktree policy

The Pi checkout is a clean deployment/test worktree, not a second authoring
location. The `PI_POC_REPO` value selects exactly which POC is tested when a Pi
hosts multiple POCs; it is intentionally not stored in Git. The authoritative
branch, Draft PR, full-SHA checkout, immutable-tag, and artifact-transfer rules
are in [the workflow](../docs/audio_poc_workflow.md).

## M1 native audio capability

After a passing environment pre-test and an exact clean Pi checkout, run the
Pi-local M1 capability packet from the repository root:

```sh
bash poc_audio/tools/m1_native_audio_capability.sh
```

The packet uses direct ALSA `hw:` devices. Capture data is discarded to
`/dev/null`, and output probes play digital silence from `/dev/zero`; it does
not retain raw audio. It records only hardware/audio facts, the repository
SHA, PCM probe results, lifecycle/concurrent results, and cleanup state.

Raw run directories under `poc_audio/evidence/m1/<timestamp>-native/` are
Git-ignored. Review them locally and publish only a sanitized M1 evidence
summary. Optional `M1_CAPTURE_DEVICE` and `M1_PLAYBACK_DEVICE` overrides must
remain operator-managed; do not commit device paths together with connection
or account information.
