# AR1M1: Runtime Feasibility and Integration Readiness

Status: `IN_PROGRESS`

Entry date: 2026-09-01

Entry baseline: `asr_r1_m0` /
`53d6c853486d625b1af9e37f7126a248f6d591f8`

AR1M1 starts with metadata-only official-source screening and fixture audit.
This entry does not authorize real artifact acquisition, build, installation,
import, model load, inference, benchmark, or Pi execution. Each real probe must
first fix an exact candidate/runtime row, controlled inputs and dependency
closure, frozen smoke fixture and method, clean full SHA, evidence location,
timeouts, and cleanup.

Bring up each official model/runtime on workstation and Pi 5 CPU-only hardware.
Run native and thin Python-adapter smoke tests with one frozen, approximately
three-second PCM fixture. Record partial/final behavior, diagnostic latency,
RTF, RSS/PSS, persistent reset, cancel, cleanup, and offline closure.

## Workstation development gate

Before scheduling Pi smoke, the workstation must pass the complete non-formal
functional suite for the candidate: exact-identity and dependency preflight,
native and thin-adapter startup, timestamped PCM input, partial/final events,
N-best fallback when supported, session isolation, persistent reset, cancel,
timeout, typed error, recovery, cleanup, bounded shutdown, offline closure, and
telemetry sanity checks. These runs may expose diagnostic timing and resources,
but they cannot publish formal scores, rankings, advance claims, or Pi
dispositions.

The Pi 5 then repeats the frozen critical smoke and lifecycle cases at the same
clean SHA to establish aarch64, CPU-only, resource, temperature/throttling, and
hardware behavior. Only Pi evidence may support target-runtime feasibility;
workstation success is necessary but not sufficient.

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
5. Advance only a workstation-complete row to the same-SHA Pi smoke. Preserve
   every failed or conditional row; do not spend a higher-cost stage to answer a
   question already closed by a lower-cost stage.

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

## Fixture gate

Before the first real smoke run, audit the historical catalogs for identity,
authorization, sensitivity, category, prior use, reference, checksum, license,
and controlled locator. Select and freeze one suitable, approximately
three-second PCM smoke fixture. Collect a replacement only when the audit
documents that no existing authorized fixture is suitable; this smoke fixture
cannot later become final holdout.

Before AR1M1 exit, complete the product-coverage matrix. Collect only the
minimum authorized prerecorded audio or annotations needed to close documented
gaps, and complete references, checksums, sensitivity, license, and prior-use
review. Propose disjoint development, adjustment, regression, and final-holdout
roles. No role becomes formal and no holdout may be inspected until User review
and the AR1M2 entry freeze.
