# Response: bounded-input Q8 and minimal CPU investigation

- **Response ID**: `RESP-POC-AUDIO-PERF-2026-001`
- **Feedback ID**: `POC-AUDIO-PERF-2026-001`
- **Status**: `REVIEWED BOUNDED DIAGNOSTIC — Q8 QUALITY NOT ADVANCED`
- **Branch**: `audio`
- **Submission HEAD**: commit containing this reviewed response
- **Tested implementation SHA**: `fd51a4f36da61fa9af7e210c7dec0170b0cffcbc`

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

## Reviewed Pi result

The clean Pi checkout at the tested SHA completed both isolated builds and all
four screenings. The generic/native comparison used the same 4.45-second
bounded input: generic/four-thread took 11.046 s, while native/four-thread took
4.031 s, a 2.74x native-build improvement. This ratio must not be attributed to
VAD trimming. The historical 11.080 s p95 used full 6/8-second fixtures and is
only a cross-packet observation. Generic bounded latency remaining at 11.046 s
provides no evidence that trimming alone materially improved absolute latency.
Historical full-input RTF p95 was 1.831987, versus 1.933469 in the new
bounded/native suite, so cross-packet RTF did not improve. The shorter
denominator and fixed inference cost prevent attributing the lower absolute
latency to an overall efficiency gain.

Native one/two/four-thread latency was 12.662/6.795/4.031 s, with effective CPU
use of 1.000/1.997/3.958 cores. The selected four-thread profile used all four
cores at 99.504–100% and 2.8 GHz without throttle. Its 50-fixture x two-hot-cycle
run produced these reviewed results:

- input duration 1.74–4.45 s, median 3.13 s and mean 3.1866 s;
- controller latency p50 4.042 s and p95 4.139 s;
- input RTF p50 1.307 and p95 1.933, meeting the retained 2.0 observation;
- peak RSS 555.438 MiB;
- 34% overall sentence correctness and 5.429864% Taiwan-Mandarin core CER;
- 50/50 deterministic fixture hypotheses across both cycles;
- no playback/capture, no throttle and clean process/device teardown.

Overall quality remains below the frozen 70% sentence-correctness gate. The
category split was 70% Taiwan Mandarin, 10% code switch, 33.333333% dates and
0% for both numbers and product terms. A private six-sample semantic check
confirmed that benign Mandarin surface errors may remain understandable, but
changed English terms, numeric nouns, frame terms and product names are unsafe
to reconstruct with an LLM. Raw transcript remains outside Git.

The reviewed sanitized evidence and raw-report checksums are indexed at
`poc_audio/evidence/m2/POC-AUDIO-PERF-2026-001/README.md`.

## Recommendation after review

Do not advance small Q8 as an M2 finalist from this diagnostic. It now has a
credible native/four-core CPU profile and meets the RTF observation, but fails
frozen overall quality and still needs about four seconds with CPU capacity
exhausted. Product/Core must decide the pending absolute-latency scope change.

For the next authorized model, use a low-cost screen before any full suite:
load once, run the six representative semantic failures once each, then run the
longest bounded fixture once for latency and RSS. Stop unless critical entity
recognition improves clearly. Medium is recommended as the next quality probe;
its exact quantization, artifact and checksum require Product/Core row approval.
Only a clear step change unlocks another 50-fixture x two-hot-cycle diagnostic.
Q5, base and HAT remain deferred meanwhile.

Two cheap same-input performance probes remain untested: flash attention and
OpenBLAS. They may be screened once on the longest fixture after authorization,
but are not expected to improve quality; OpenMP is lower priority because the
existing internal worker already saturates all four cores. Initial prompts or
domain vocabulary may help technical entities, but change the frozen decoding
configuration and can add biased guesses. Streaming is an integrated-pipeline
change, and HAT needs a separate converted model/backend rather than the GGML
binary. None is implicitly authorized by this response.

## Reproduction entry points

- Build: `poc_audio/tools/run_m4a_whispercpp_build.sh ... --build-profile generic|native`
- Bounded screening/diagnostic: `poc_audio/tools/run_m4a_whispercpp_bounded.sh ...`
- Sanitized evidence index: `poc_audio/evidence/m2/POC-AUDIO-PERF-2026-001/README.md`

The first run at submitted SHA `5964d9683b538acd37e11197e60cbe4640ff604d`
stopped before inference because the frozen label index used the current
`records[]` shape. The rejected finding was retained and parser support was
appended in the tested SHA; the previously submitted SHA was not rewritten.
