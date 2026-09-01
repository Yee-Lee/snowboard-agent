# AR1 Implementation Root

This directory contains AR1 source, tests, schemas, manifests, tools,
deliveries, and sanitized evidence. AR1M1 adds exact-identity preflight, native
backends, a thin streaming adapter, lifecycle and paced-latency probes,
process-tree telemetry, offline auditing, and diagnostic VAD/scorer scaffolds.
All five rows have completed non-formal development bring-up on an x86_64
Ubuntu 24.04 virtual machine limited to 2 vCPUs. Those measurements are not Pi
5 evidence, and models, runtimes, audio, and raw results remain outside Git.
Legacy code remains available at immutable tag `audio_m4` and must not be
imported directly.

Default local verification is:

```text
python3 -m unittest discover -v
python3 -m asr_r1.tools.check_data_safety
python3 -m asr_r1.tools.check_m0_readiness
python3 -m asr_r1.tools.check_m1_workstation_readiness
```

The readiness command verifies the immutable M0 foundation. M1 remains in
progress until its clean-SHA workstation repetition, fixture gate, and real Pi
5 critical smoke/lifecycle evidence are complete.
