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

## M1 deterministic fake baseline

The M1 harness uses Python 3.11 or newer and the standard library only. The
tracked `requirements.lock` intentionally has no third-party packages. Run the
local unit tests first:

```sh
PYTHONPATH=poc_audio/src \
  python3 -m unittest discover -s poc_audio/tests -v
```

After committing the implementation so the worktree is clean and has a full
test SHA, run the formal fake baseline:

```sh
bash poc_audio/tools/run_m1_fake_baseline.sh
```

It starts deterministic child processes and proves success, declared error,
timeout, task cancellation, forced abort, and zero-child cleanup. Raw JSON
results are written to a Git-ignored timestamp directory under
`poc_audio/evidence/m1/`. Publish only the reviewed sanitized summary.

The tracked fixture catalog currently covers deterministic fake inputs only.
It validates harness plumbing but does not authorize real candidate runs; the
licensed VAD/ASR audio catalog and its labels/checksums remain an M1 gate.

## M1 authorized fixture recording

The controlled VAD/ASR recording plan and authorization boundary are in
[`fixtures/authorized/`](fixtures/authorized/README.md). The interactive
recorder captures only direct native PCM into a Git-ignored local directory;
it requires `--confirm-authorization` before it can start `arecord`.

```sh
bash poc_audio/tools/m1_fixture_record.sh --list
```

Do not run the recording command until the User/Designer has confirmed the
internal-only recording authorization. A completed recording set still needs
checksum/metadata review and the pinned conversion boundary before it becomes a
candidate fixture.

### M2 Gate 1B authorized artifact preflight

Only the Core-ACKed SenseVoice ASR and Matcha TTS rows may enter this check. On
the Pi, point it at the external controlled artifact directory before any
install/import/load. It verifies exact filename, byte size and SHA-256 and
writes a report that explicitly remains `PREFLIGHT_PASS_NOT_EXECUTED`:

```bash
bash poc_audio/tools/run_m4a_authorized_preflight.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --output /tmp/m4a-authorized-preflight.json
```

The check is offline and does not install or execute a candidate runtime.

## M1 P4 Option A validation packet

Prepare the P4-A01 through P4-A10 evidence structure only after local tests
pass. A formal packet requires a clean worktree and records the exact full Git
SHA plus checksums for the runner, deterministic fixture definitions, and
sanitized config:

```sh
bash poc_audio/tools/run_option_a_validation.sh prepare
```

The command creates a timestamped, Git-ignored directory under
`poc_audio/evidence/m3_option_a/`. It does not open an audio device or execute a
hardware test. All ten results begin as `Pending`. Validate a packet after any
controlled evidence update with:

```sh
bash poc_audio/tools/run_option_a_validation.sh validate \
  poc_audio/evidence/m3_option_a/<timestamp>/manifest.json
```

Do not use `--allow-dirty` for evidence submitted to Core; that switch exists
only for local runner development and tests.

After installing the pinned candidate artifacts in an isolated Pi environment,
run deterministic P4-A03 through A05 conversion validation with:

```sh
bash poc_audio/tools/run_option_a_conversion.sh \
  poc_audio/evidence/m3_option_a/<timestamp>/raw/conversion
```

The deterministic mapping in this runner validates the conversion seam only.
It does not select the target microphone channel or valid-bit alignment; those
remain P4-A02 evidence decisions.

Analyze an authorized native fixture directory for channel and S32 valid-bit
evidence without emitting audio samples:

```sh
bash poc_audio/tools/run_option_a_valid_bits.sh \
  poc_audio/fixtures/artifacts/<authorized-pilot> \
  poc_audio/evidence/m3_option_a/<timestamp>/raw/valid-bits.json
```

The raw-analysis result must be reviewed together with wiring attestation and
the prior human check of known fixture labels before P4-A02 can pass.

For P4-A06 through A09 only, run the live Pi packet from the isolated candidate
environment with direct `hw:` capture and playback devices. It records a
five-minute concurrent session, heartbeat, cancel/reopen/failure cleanup and
resource samples; review the raw JSON before assigning any P4 status:

```sh
bash poc_audio/tools/run_option_a_live.sh \
  --capture-device hw:<card>,<device> \
  --playback-device hw:<card>,<device> \
  --output poc_audio/evidence/m3_option_a/<timestamp>/raw/p4-a06-a09.json
```

For the Core-approved P4-A10 reproducibility rerun, place only the checked
source archives and build wheels in an external artifact directory, then run a
fresh offline build. The output path must be new and belongs under the packet's
ignored `raw/` directory. The runner verifies every declared SHA-256, injects
the pinned CMake dependencies without network fetches, builds both sources,
and performs an independent install/import identity rerun:

```sh
bash poc_audio/tools/run_option_a_a10_clean_build.sh \
  --artifact-dir /controlled/p4-a10-artifacts \
  --output poc_audio/evidence/m3_option_a/<timestamp>/raw/a10-clean-build
```

## M1 Pilot ASR preflight

The complete 40-item Pilot may be used only for the approved observation-only
ASR input/runtime preflight. It does not freeze the fixture set or permit an
ASR advance/reject decision. Read
[`fixtures/authorized/pilot_asr_preflight.md`](fixtures/authorized/pilot_asr_preflight.md)
before preparing local derived WAVs.
