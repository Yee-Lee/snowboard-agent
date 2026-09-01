# AR1M1: Runtime Feasibility and Integration Readiness

Status: `COMPLETE`

Entry date: 2026-09-01

Completion date: 2026-09-01

Entry baseline: `asr_r1_m0` /
`53d6c853486d625b1af9e37f7126a248f6d591f8`

AR1M1 started with metadata-only official-source screening and fixture audit.
Each real workstation probe then fixed an exact candidate/runtime row,
controlled inputs and dependency closure, frozen smoke fixture and method,
clean full SHA, evidence location, timeouts, and cleanup.

The completed M1 scope is official model/runtime workstation development and
non-formal feasibility verification. It runs native and thin Python-adapter
smoke tests with one frozen, approximately three-second PCM fixture and records
partial/final behavior, diagnostic latency, RTF, RSS/PSS, persistent reset,
cancel, cleanup, and offline closure. It does not claim Raspberry Pi 5
execution, formal scores, comparative rankings, or target-hardware
qualification.

## Workstation development gate

The workstation must pass the complete non-formal functional suite for the
candidate: exact-identity and dependency preflight,
native and thin-adapter startup, timestamped PCM input, partial/final events,
N-best fallback when supported, session isolation, persistent reset, cancel,
timeout, typed error, recovery, cleanup, bounded shutdown, offline closure, and
telemetry sanity checks. These runs may expose diagnostic timing and resources,
but they cannot publish formal scores, rankings, advance claims, or Pi
dispositions.

At AR1M2 entry, before formal scoring, the Pi 5 repeats the frozen critical
smoke and lifecycle cases at an immutable delivery SHA to establish aarch64,
CPU-only, resource, temperature/throttling, and hardware behavior. Only Pi
evidence may support target-runtime feasibility; completed M1 workstation
development remains necessary but not sufficient.

## Minimum-cost probe order

Apply the same fail-closed order to every candidate:

1. Verify an official immutable checkpoint, runtime, license/notice, supported
   streaming contract, and credible workstation/aarch64 path using metadata
   only. Record `LOCKABLE`, `CONDITIONAL`, or `STOP` without downloading a
   model.
2. For a lockable row, freeze source URLs/revisions, filenames, declared sizes,
   expected checksums, dependency closure, offline recipe, fixture, commands,
   timeouts, evidence, and cleanup at a clean SHA.
3. Acquire the smallest exact official artifact set into controlled storage and
   verify identities before unpack, install, import, or load. Stop on mismatch.
4. Run the cheapest official native workstation startup and one frozen smoke;
   then run the thin adapter and complete non-formal functional/lifecycle suite.
5. Preserve every failed or conditional row and hand workstation-complete rows
   to the AR1M2 entry gate. Do not spend a higher-cost stage to answer a question
   already closed by a lower-cost stage.

Prove a fake VAD/fake scorer scaffold and investigate N-best, confidence,
timestamp, endpoint, and future scorer directions. Produce probe dispositions
and advance/conditional/stop advice, not formal rankings.

## Frozen workstation baseline order

The User-directed M1 development order is:

1. sherpa-onnx streaming Zipformer zh x-large INT8 2025-06-30.
2. sherpa-onnx WeNet WenetSpeech streaming CTC INT8, 133,162,857-byte model.
3. NVIDIA Nemotron 3.5 ASR Streaming 0.6B portable Q8_0.
4. sherpa-onnx streaming Zipformer zh large INT8 2025-06-30.
5. sherpa-onnx WeNet AISHELL streaming CTC INT8, 49,618,814-byte model.

This is a cost/probe sequence, not a quality score or formal ranking. The WeNet
rows exercise sherpa-onnx online CTC conversions; they do not claim that native
U2++ attention rescoring was tested. PengChengStarling is preserved as stopped
after the User eliminated its 1,220,027,735-byte unquantized inference closure.

The baseline uses `asr-clear-002-p0`, a frozen 2.66-second regression smoke,
deterministic 160 ms chunks, CPU only, and a 1,000,000,000-byte RSS reference.
Each row must return a non-empty final and record model load time when exposed,
warm decode wall time, RTF, peak RSS, and an above-reference flag. RSS does not
terminate or eliminate a POC row. The controlled source WAV has been recovered
and the p0 crop reproduces the frozen checksum. Artifact acquisition and
execution require this revised method at a clean SHA.

The confirmed target and completed pre-execution research are consolidated in
[`AR1M1 Target and Completed Feasibility Research`](../research/ar1_m1_target_and_feasibility.md).
It remains the identity baseline; current development execution is documented
separately.

## Completed workstation development state

All five exact candidates have completed native and thin-adapter development
bring-up, paced TTFT and speech-end timing, unpaced full-utterance RTF,
lifecycle, resource, and syscall-level offline probes. The clean-SHA
workstation repetition completed at runtime-harness SHA
`f478f4baab39c99c361e63bb9d956f09384efecc` and append-only offline-audit-fix
SHA `55c28ab0eef50ba41dbee1ac1abc6a162f2bb2a6`; no further workstation model
rerun is pending. The environment is an x86_64 Ubuntu 24.04 virtual machine
with 2 vCPUs and CPU-only execution. It is not Raspberry Pi 5 or aarch64
evidence. The implementation and sanitized breakdown are documented in
[`AR1M1 Workstation Development Report`](../research/ar1_m1_workstation_development_report.md).

The runs remain explicitly non-formal. On 2026-09-01 the User reviewed this
scope boundary, directed minimum fixture gap collection to AR1M2 entry, and
approved closing AR1M1. Real Pi 5 critical smoke/lifecycle evidence remains an
AR1M2 pre-formal entry gate and is not implied by this completion.

## Fixture gate

Before the first real smoke run, audit the historical catalogs for identity,
authorization, sensitivity, category, prior use, reference, checksum, license,
and controlled locator. Select and freeze one suitable, approximately
three-second PCM smoke fixture. Collect a replacement only when the audit
documents that no existing authorized fixture is suitable; this smoke fixture
cannot later become final holdout.

For AR1M1 exit, complete the product-coverage matrix at metadata level and
document every gap with its minimum closure action. By User direction, collect
or derive the minimum authorized prerecorded audio or annotations at AR1M2
entry, then complete references, checksums, sensitivity, license, and prior-use
review. No role becomes formal and no holdout may be inspected until User
review and the AR1M2 entry freeze. The schedule-only revision is recorded in
`asr_r1/manifests/m1_fixture_schedule_revision.json`.

## Completion evidence

- All five exact candidates passed native, thin-adapter, lifecycle, offline,
  timeout, recovery, cleanup, and telemetry development checks.
- Runtime-harness SHA `f478f4baab39c99c361e63bb9d956f09384efecc`
  and append-only offline-audit-fix SHA
  `55c28ab0eef50ba41dbee1ac1abc6a162f2bb2a6` identify the clean execution
  implementations.
- The complete repository test suite, compilation, data-safety, readiness,
  clean-tree, and relocated-checkout checks passed.
- Failed attempts and rows above the RSS reference remain preserved.
- Results are x86_64 Ubuntu 24.04, 2-vCPU, CPU-only, non-formal diagnostics and
  explicitly not Raspberry Pi 5 evidence.
- User approved the scope revision and AR1M1 closure on 2026-09-01.

AR1M1 completion is identified by immutable annotated tag `asr_r1_m1`.
