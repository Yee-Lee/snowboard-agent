# AR1M1: Runtime Feasibility and Integration Readiness

Status: `NOT_STARTED`

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

Prove a fake VAD/fake scorer scaffold and investigate N-best, confidence,
timestamp, endpoint, and future scorer directions. Produce probe dispositions
and advance/conditional/stop advice, not formal rankings.

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
