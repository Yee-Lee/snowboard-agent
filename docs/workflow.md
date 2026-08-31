# ASR R1 Workflow

Status: `AUTHORITATIVE`

AR1 evaluates low-latency, local, streaming ASR on Pi 5 CPU-only hardware. The
permanent branch is `asr_r1`; historical control is `audio_m4` at
`5694ead4ba6be928fdb4dbdf6da7155b214d72bd`; milestone tags are immutable
`asr_r1_m0` through `asr_r1_m4`.

Workstation changes precede Pi execution. Before formal evidence, converge work
into a clean candidate commit. A submitted or tested SHA is immutable; append
fixes on top.

Developer prepares source and a full SHA. Tester checks out that exact SHA on
Pi, verifies a clean tree and environment, runs the frozen packet, and returns
controlled raw evidence. Technical Lead reviews results without changing the
method. User performs target-hardware and product trade-off review.

Every candidate fixes engine, checkpoint, runtime, build, quantization,
configuration, dependencies, source/license, size, and checksum. Models and
runtime artifacts stay in controlled storage. Formal offline runs use a clean,
pre-acquired dependency closure.

Every formal packet records requirement, preconditions, SHA, hardware,
commands, repeats, method, evidence, and cleanup. Private audio, sensitive
transcripts, credentials, endpoints, models, binaries, wheels, and raw output
never enter Git.

Do not start a later milestone silently. Update the milestone index when status,
reachability, evidence, risks, or authorized next work changes.
