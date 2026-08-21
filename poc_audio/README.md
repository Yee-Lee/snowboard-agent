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

The fixture-delivery unit test uses a deterministic injected resampler, so this
suite does not depend on a workstation `samplerate` installation. Real fixture
delivery still runs only through `m1_fixture_delivery.sh`, whose preflight
requires the separately built and verified Option A runtime containing
`samplerate 0.2.4`; a test substitute is never selected by the CLI.

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

### M2 ACK-003 comparative packet

ACK-003 supersedes the old ASR execution order and quality/performance
elimination gates below. The current M2A entry point is the shared comparative
packet; validate it before resolving any controlled fixture or acquiring a model:

```bash
bash poc_audio/tools/run_m4a_m2a_packet.sh --validate-only
```

The tracked packet pins eight required/optional ASR rows, official artifact and
runtime identities, deterministic internal/Common Voice selection rules, bounded
budgets and observation-only dispositions. It remains
`LOCKED_NOT_EXECUTED`: the frozen internal exact-eight and authenticated Common Voice
26.0 zh-TW exact-twelve sources have produced the reviewed 20-item 16 kHz mono S16_LE
fixture lock. No candidate has built, loaded or executed; each row still requires its
exact artifact/runtime/license preflight. See
[`M4A-M2A-COMMON-PACKET-001`](deliveries/M4A-M2A-COMMON-PACKET-001.md) for the
controlled preparation command and current blocker.

After one row's exact artifact and runtime closure has been reviewed on the clean Pi
candidate SHA, execute it through `run_m2a_survey.sh`. The runner verifies the tracked
and controlled fixture locks, enters an isolated network namespace, performs one
warm-up and one scored inference for every item, writes raw transcripts only to the
controlled output, and emits a separate sanitized row report. It never opens capture
or playback devices. Each engine uses explicit arguments; for example, a whisper.cpp
row supplies `--binary`, `--model`, and the identical `--artifact`, while Python rows
supply `--runtime-python`, `--model-dir`, and the archived `--artifact`. Every row also
supplies `--runtime-artifact-dir`; the runner checks every source/wheel byte identity
from the packet before loading a model. The Vosk eleven-wheel closure is pinned for
internal survey use, while its upstream wheel's missing license notice remains an
explicit redistribution-review risk.

#### Historical ACK-001 artifact preflight

Only the Core-ACKed SenseVoice ASR and Matcha TTS rows may enter this check. On
the Pi, point it at the external controlled artifact directory before any
install/import/load. It verifies exact filename, byte size and SHA-256 and
writes a report that explicitly remains `PREFLIGHT_PASS_NOT_EXECUTED`:

```bash
bash poc_audio/tools/run_m4a_authorized_preflight.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --output /tmp/m4a-authorized-preflight.json
```

The check is offline and does not install or execute a candidate runtime. It is
preserved for the historical ACK-001 evidence path and is not the ACK-003 M2A
entry point.

#### Historical ACK-002 whisper.cpp recovery

The rejected SenseVoice evidence and its historical runner remain unchanged.
For the historical ACK-002 ASR recovery, the separate runner verifies the exact
whisper.cpp source archive, selected small model and all required notices. Its
default was Q8_0; its Q5_1 conditional trigger is retained only to reproduce the
old evidence and has been removed from the current ACK-003 M2A ordering:

```bash
bash poc_audio/tools/run_m4a_whispercpp_preflight.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --output /tmp/m4a-whispercpp-artifact-preflight.json
```

The controlled store must contain `sources/` and `models/` at the ACK locators,
plus `notices/model-repository-LICENSE`,
`notices/whispercpp-model-documentation.md` and
`notices/upstream-whisper-lineage.md`. A pass is artifact-only and explicitly
reports `BUILD_NOT_RUN`; it does not authorize inference until the CPU-only
CMake cache, binary identity, dynamic dependencies and offline build evidence
have also been reviewed.

On the clean Pi Candidate SHA, disconnect network routes and run the separate
build closure into a new external directory:

```bash
bash poc_audio/tools/run_m4a_whispercpp_build.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --work-dir /controlled/audio-poc/work/whispercpp-q8-build-001 \
  --output /tmp/m4a-whispercpp-build.json
```

The runner preserves a read-only handle to its caller network namespace, creates
its own user/network namespace, and refuses non-Pi 5/aarch64/Debian 13 hosts, a
dirty checkout, reused work/output paths, an unchanged network namespace, a non-loopback default route
or any non-loopback network interface in the namespace-scoped `/proc` view. It checks isolation before and
after building only the
bounded persistent `m4a-whispercpp-worker`, verifies every frozen CMake cache
flag, rejects prohibited dynamic dependencies, and records toolchain, commands, binary checksum and
`ldd`. Its success status still says model not loaded and inference not run.

After artifact and build reports are reviewed, run Q8 qualification from the
same clean Candidate SHA. The runner uses one persistent model process, four
compute threads, the frozen 50-item set, three cold suites, three warmups and
twenty hot suites. It hashes transcripts instead of storing them and never
opens capture or playback devices:

```bash
bash poc_audio/tools/run_m4a_whispercpp_qualification.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --fixture-dir /controlled/audio-poc/fixtures/delivered-option-a-v1 \
  --binary /controlled/audio-poc/work/whispercpp-q8-build-001/build/bin/m4a-whispercpp-worker \
  --build-report /tmp/m4a-whispercpp-build.json \
  --work-dir /controlled/audio-poc/work/whispercpp-q8-qualification-001 \
  --output /tmp/m4a-whispercpp-q8-qualification.json
```

The raw report remains `UNREVIEWED`. Under historical ACK-002 only, Q5 required a
separately reviewed Q8 report from the same Candidate SHA and unlocked only when
Q8 passed both quality gates while latency exceeded 1.5 seconds or peak RSS
exceeded 1250 MiB. ACK-003 supersedes that execution rule; do not use this runner
to decide the current M2A order.

When the operator explicitly chooses an early directional read instead of the
frozen packet, append `--diagnostic-hot-repetitions 2`. This skips cold suites,
retains all three warmups, and measures two complete 50-item hot cycles. Its
report is always marked `PARTIAL_DIAGNOSTIC_NOT_GATE_EVIDENCE`; it cannot pass a
gate or unlock Q5, and the full 20-repetition run remains pending.

#### Historical VAD-label-bounded Q8 investigation

For `POC-AUDIO-PERF-2026-001`, preserve the historical runner above and create
new generic/native builds with `--build-profile`. Native changes only
`GGML_NATIVE` from `OFF` to `ON`; OpenMP and BLAS remain disabled:

```bash
bash poc_audio/tools/run_m4a_whispercpp_build.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --work-dir /controlled/audio-poc/work/whispercpp-q8-native-build-001 \
  --output /tmp/m4a-whispercpp-q8-native-build.json \
  --build-profile native
```

After reviewing both build reports, run the longest-fixture screening with
generic/4 threads and native/1,2,4 threads. Then run only the selected
four-thread profile over all 50 fixtures for two hot cycles:

```bash
bash poc_audio/tools/run_m4a_whispercpp_bounded.sh \
  --artifact-dir /controlled/audio-poc/gate1b \
  --fixture-dir /controlled/audio-poc/fixtures/delivered-option-a-v1 \
  --vad-label-index /controlled/audio-poc/fixtures/review/vad-labels-v1.json \
  --binary /controlled/audio-poc/work/BUILD/build/bin/m4a-whispercpp-worker \
  --build-report /tmp/BUILD.json \
  --work-dir /controlled/audio-poc/work/q8-bounded-two-hot \
  --output /tmp/q8-bounded-two-hot.json \
  --mode diagnostic --threads 4 --hot-repetitions 2
```

The runner checks the exact frozen label checksum and creates contiguous WAVs
from first labelled speech start through last labelled speech end, preserving
all internal pauses. Derived audio/raw reports remain outside Git. It records
controller/native/CPU time, input and labelled speech duration, RTF, RSS,
task/core utilization, governor/frequency, thermal and cleanup. It never opens
an audio device or plays sound. Absolute final-transcript latency is an M2
observation in this packet; all other frozen gates remain unchanged.

#### ACK-001 historical SenseVoice/Matcha runners

The following preserved commands reproduce the already-reviewed ACK-001
SenseVoice/Matcha path; they are not prerequisites or fallbacks for ACK-002.
For that historical path, create a new isolated runtime and
prove exact offline install/import identity without extracting or loading a
model, running inference, or opening an audio device:

```bash
bash poc_audio/tools/run_m4a_runtime_preflight.sh \
  --artifact-dir poc_audio/artifacts/gate1b \
  --runtime-dir /controlled/audio-poc/runtime/sherpa-onnx-1.13.5 \
  --output /tmp/m4a-runtime-preflight.json
```

The runtime and output paths must both be new. The runner accepts only Pi 5,
aarch64 and Python 3.13, installs the two authorized wheels with `--no-index`
and `--no-deps`, records package/native-library identity, and leaves both
candidate models unloaded.

The first real-candidate smoke remains preliminary and does not play audio. It
uses frozen `asr-clear-001` plus tracked `tts-001`, extracts both exact archives
into a new external work directory, and returns ASR quality counts/hash and TTS
native PCM metadata without storing transcript or PCM bytes:

```bash
bash poc_audio/tools/run_m4a_candidate_smoke.sh \
  --artifact-dir poc_audio/artifacts/gate1b \
  --runtime-dir /controlled/audio-poc/runtime/sherpa-onnx-1.13.5 \
  --fixture-dir /controlled/audio-poc/fixtures/delivered-option-a-v1 \
  --work-dir /controlled/audio-poc/work/smoke-001 \
  --output /tmp/m4a-candidate-smoke.json
```

This smoke cannot close the frozen 50-item ASR, 20-prompt TTS, lifecycle,
resource, User-quality, or Gate 2A requirements.

### Historical ACK-001 full-fixture qualification without playback

After the focused smoke passes, use a new work directory and output file to run
the frozen three cold suites and twenty hot suites for both authorized rows.
The runner verifies all 50 delivered ASR WAV checksums, all 20 tracked TTS
prompts and every authorized candidate artifact before loading a model. It
never writes PCM, opens ALSA or plays a speaker:

```bash
bash poc_audio/tools/run_m4a_qualification.sh \
  --artifact-dir poc_audio/artifacts/gate1b \
  --runtime-dir /controlled/audio-poc/runtime/sherpa-onnx-1.13.5 \
  --fixture-dir /controlled/audio-poc/fixtures/delivered-option-a-v1 \
  --work-dir /controlled/audio-poc/work/qualification-001 \
  --output /tmp/m4a-qualification.json
```

The report may close only the full-fixture ASR quality and TTS latency/RTF
observations. Candidate lifecycle, network-disabled P12 evidence, RSS-growth
review and User TTS quality review remain explicit pending items. Keep the raw
JSON outside Git and commit only a reviewed sanitized evidence summary.

After reviewing the full-fixture result, exercise the still-eligible Matcha
persistent-child lifecycle with a new work/output pair:

```bash
bash poc_audio/tools/run_m4a_tts_lifecycle.sh \
  --artifact-dir poc_audio/artifacts/gate1b \
  --runtime-dir /controlled/audio-poc/runtime/sherpa-onnx-1.13.5 \
  --work-dir /controlled/audio-poc/work/tts-lifecycle-001 \
  --output /tmp/m4a-tts-lifecycle.json
```

The packet runs success, declared error, timeout, cancel, force-abort, five
reopen cycles and a `strace` network-syscall observation. Matcha generates only
in-memory metadata; the worker emits no PCM and never opens playback. A zero
network-syscall trace while networking remains enabled does not close P12;
network-disabled evidence still requires an approved isolation method or an
operator-approved temporary network change.

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
