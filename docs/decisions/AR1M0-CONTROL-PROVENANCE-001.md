# AR1M0 Whisper and Silero Control Provenance Decision

- **Status**: `FROZEN FOR AR1 PLANNING / EXECUTION NOT AUTHORIZED`
- **Date**: 2026-09-01
- **Historical control**: `audio_m4` /
  `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`
- **Machine-readable record**:
  `asr_r1/manifests/control_provenance.json`

AR1 records the accepted historical Whisper.cpp 1.9.2 base-Q8 and Silero VAD
6.2.1 identities, configurations, checksums, and exact `audio_m4` source
references. These facts establish comparison provenance only. They do not copy
old evidence into AR1, grant acceptance credit, or authorize acquisition,
build, load, inference, benchmark, or Pi execution.

AR1M1 must reacquire or rebuild every required source, runtime, model, and
dependency from controlled immutable inputs, verify size, checksum, license,
notice, platform compatibility, and offline closure, then publish a new clean
candidate SHA and frozen packet before real execution. Historical binaries are
never treated as AR1 execution artifacts.
