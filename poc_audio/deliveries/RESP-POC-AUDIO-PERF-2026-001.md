# Response: bounded-input Q8 and minimal CPU investigation

- **Response ID**: `RESP-POC-AUDIO-PERF-2026-001`
- **Feedback ID**: `POC-AUDIO-PERF-2026-001`
- **Status**: `IMPLEMENTATION CANDIDATE — PI EVIDENCE PENDING`
- **Branch**: `audio`
- **Submission HEAD**: commit containing the completed reviewed evidence response
- **Tested implementation SHA**: pending clean-Pi execution

## Accepted direction and decision boundary

The historical small-Q8 report at implementation SHA
`1b29f685de64970f6abbc12a0820a2ef4ec0a444` remains unchanged: complete 6/8-second
inputs, generic build, 11.080 s hot final-transcript p95, RTF p95 1.831987,
9.502262% Taiwan-Mandarin core CER, 28% sentence correctness and 554 MiB peak
RSS. It is not relabelled or deleted.

For the current M2 investigation, final-transcript p95 is an observation only.
The <=1.5 s hard gate is requested to move to future integrated VAD-to-ASR
validation with separately frozen start/end timestamps. RTF p95 <=2.0 and all
frozen quality, resource, determinism, offline and lifecycle boundaries remain.
This is a recorded scope change, not a retroactive pass. A final Q8 finalist or
no-go decision remains pending Product/Core acceptance of that scope.

Q5, base, medium and HAT investigation are deferred until this bounded Q8 work
is reviewed.

## Deterministic bounded input

The runner verifies the frozen VAD label index SHA-256
`85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74`, the frozen
recording plan and all 50 delivered fixture hashes. For each fixture it creates
one contiguous 16 kHz mono S16_LE WAV from the first labelled speech start to
the last labelled speech end. All samples between those boundaries, including
the reviewed internal pause, are preserved. Speech intervals are never
concatenated, the source WAV is never changed, and no artificial duration is
imposed.

Derived WAVs and their full manifest remain in the external controlled work
directory. The report binds the label, source-set and derived-manifest
checksums, total input duration and total labelled speech duration. No PCM or
transcript is committed.

## Minimum-cost build and runtime investigation

Only two builds are permitted for this packet:

1. `generic`: the historical CPU-only CMake flags, including
   `GGML_NATIVE=OFF`, `GGML_OPENMP=OFF` and `GGML_BLAS=OFF`.
2. `native`: identical to `generic` except `GGML_NATIVE=ON`.

Each build report records compiler/CMake identity, Release flags, `lscpu`,
detected `GGML_CPU_ARM_ARCH`, final CMake cache, compile-command checksum,
binary checksum and dynamic dependencies. OpenMP and BLAS are inspected but
not benchmarked because they add another variable/dependency and are not
needed for the first decision.

Use the longest derived fixture for four screening inferences: generic at four
threads and native at one, two and four threads. Record controller/native/CPU
time, RTF, effective CPU cores, worker task count, active tasks, per-thread CPU
time, cores used, per-core utilization, governor/frequency, temperature and
throttle state. Select the four-thread profile only after this comparison; if
native build/preflight or screening is invalid, retain generic.

Run the selected profile over all 50 bounded fixtures for exactly two hot
cycles after three unscored warmups. Do not run cold suites or 20 repetitions.
This remains diagnostic evidence, but is sufficient for the requested Q8
opportunity assessment.

No command in this packet opens capture/playback devices or emits speaker
audio. Inference runs in the existing isolated network namespace and must end
with zero worker/device owners.

## Reproduction entry points

- Build: `poc_audio/tools/run_m4a_whispercpp_build.sh ... --build-profile generic|native`
- Bounded screening/diagnostic: `poc_audio/tools/run_m4a_whispercpp_bounded.sh ...`
- Sanitized evidence index: `poc_audio/evidence/m2/POC-AUDIO-PERF-2026-001/README.md`

The final evidence update will record the exact submission/test SHA, complete
commands, build and input identities, raw-report checksums, reviewed metrics,
cleanup proof and Q8 disposition recommendation.
