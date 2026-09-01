# ASR R1 Workflow

Status: `AUTHORITATIVE`

AR1 evaluates low-latency, local, streaming ASR on Pi 5 CPU-only hardware. The
permanent branch is `asr_r1`; historical control is `audio_m4` at
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`; milestone tags are immutable
`asr_r1_m0` through `asr_r1_m4`.

Workstation changes precede Pi execution. Before formal evidence, converge work
into a clean candidate commit. A submitted or tested SHA is immutable; append
fixes on top.

The workstation is the complete development-test environment. It must run all
non-formal functional coverage: schemas, manifests, fake/unit tests, native and
thin-adapter contracts, lifecycle, partial/final behavior, N-best fallback,
cancel, timeout, typed error, recovery, reset, cleanup, offline/dependency
preflight, and telemetry sanity checks. Formal scoring or comparative results
and integrated product qualification are Pi 5-only. At AR1M2 entry, before
formal scoring, Pi smoke repeats critical functional and lifecycle cases to
prove aarch64 and hardware behavior; workstation success never substitutes for
Pi evidence.

Developer prepares source and a full SHA. Tester checks out that exact SHA on
Pi, verifies a clean tree and environment, runs the frozen packet, and returns
controlled raw evidence. Technical Lead reviews results without changing the
method. User performs target-hardware and product trade-off review.

Explicit User approval is required before creating or pushing any commit that
contains formal scores, rankings, hardware-result dispositions, qualification
decisions, or final outcome language. Draft measurements and scorecards may be
prepared without that approval only when clearly labeled non-formal and when
they do not imply review, qualification, or acceptance.

Every candidate fixes engine, checkpoint, runtime, build, quantization,
configuration, dependencies, source/license, size, and checksum. Models and
runtime artifacts stay in controlled storage. Formal offline runs use a clean,
pre-acquired dependency closure.

Every formal packet records requirement, preconditions, SHA, hardware,
commands, repeats, method, evidence, and cleanup. Private audio, sensitive
transcripts, credentials, endpoints, models, binaries, wheels, and raw output
never enter Git.

Development code and scripts reference repository resources only through
repo-root-relative paths. Host-specific absolute paths and checkout-location
assumptions are prohibited. Path resolution must fail closed if a repository
resource would escape the current repository root.

Do not start a later milestone silently. Update the milestone index when status,
reachability, evidence, risks, or authorized next work changes.
