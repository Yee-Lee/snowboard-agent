# Audio POC ASR bounded-input and candidate investigation

- Feedback ID: `POC-AUDIO-PERF-2026-001`
- Role: Internal Engineering Reviewer
- Priority: High
- Status: Open — Ready for PM
- POC repo: `poc_audio/snowboard-agent`
- Reviewed branch / HEAD: `audio` / `b0347fe71c3af558ce9f3e2d3f1fd19cb84f48a3`
- Tested implementation SHA: `1b29f685de64970f6abbc12a0820a2ef4ec0a444`
- Related evidence: `poc_audio/evidence/m2/M4A-G1B-ASR-RECOVERY-Q8-PARTIAL-001.md`

## Conclusion and product direction

The committed Whisper.cpp small Q8 packet remains valid for its exact generic CPU build and complete 6/8-second WAV inputs. It does not represent the intended externally bounded utterance workload and does not prove effective four-thread CPU utilization.

For the current isolated M2 ASR investigation:

- retain hot RTF p95 `<= 2.0` and the frozen quality/resource/lifecycle gates;
- remove hot final-transcript p95 `<= 1.5 s` as a current hard gate and record the value as an observation only; and
- defer the absolute `1.5 s` hard gate to future integrated VAD-to-ASR validation, where its start/end timestamps must be frozen before execution.

Do not erase or relabel the existing Q8 result. Submit the revisions below before making a CPU-only ASR no-go or finalist decision.

## POC-AUDIO-PERF-2026-001 — High — Open

Issue: The current run uses complete fixed-duration WAVs, default Whisper audio context, internal VAD disabled, and a build with `GGML_NATIVE=OFF`, `GGML_OPENMP=OFF` and `GGML_BLAS=OFF`. It therefore cannot distinguish model cost from input padding, generic compilation or ineffective parallelism. The current authorized model set also does not show the quality/performance tradeoff across Whisper `base`, `small` and `medium` multilingual models.

Required revision:

1. Re-run the ASR workload using utterances derived from the existing frozen VAD labels. Do not impose an artificial two-second duration. Preserve each labelled utterance's natural duration and all labelled internal pauses; do not concatenate separated speech intervals or modify the source fixtures.
2. For the existing Q8 result and the label-bounded run, report audio duration, labelled speech duration, controller latency, native inference time, CPU time, RTF p50/p95/max, transcript quality and exact configuration. Report final-transcript latency as an observation, not an M2 hard-gate result.
3. Demonstrate actual parallel execution: configured thread count, worker task count, per-thread/per-core utilization, CPU governor/frequency, temperature and throttle state. Include controlled thread-scaling observations rather than treating `n_threads=4` as proof of four-core use.
4. Execute a controlled Pi 5 build/runtime investigation. Record compiler, build type, compile flags, detected ARM features and final `GGML_NATIVE`, `GGML_CPU_ARM_ARCH`, `GGML_OPENMP` and `GGML_BLAS` values. Change one build or runtime variable at a time, retain the generic build as baseline, and run full qualification only for configurations that pass the bounded screening.
5. Propose exact, immutable multilingual Whisper `base`, `small` and `medium` candidate rows, including quantization, source/model identity, checksum, license, Pi build profile and execution order. After row-specific written ACK, compare the authorized rows on the same label-bounded corpus and report quality, latency, RTF, RSS, CPU and thermal tradeoffs. This model comparison is required scope; it must not silently substitute a new model for the existing Q8 evidence.

Verification:

- Commit the response at `poc_audio/deliveries/RESP-POC-AUDIO-PERF-2026-001.md` and sanitized evidence index under `poc_audio/evidence/m2/POC-AUDIO-PERF-2026-001/`.
- Identify the branch, full submission HEAD, every tested implementation SHA, VAD-label index checksum, derived-input manifest checksum, source/model/binary checksums and complete reproduction commands.
- Preserve the existing `11.080 s` and RTF observations under their original SHA/configuration. New input, build or model results are additional evidence.
- Conclude which bounded-input and authorized model/build profiles meet the retained RTF, quality, resource and lifecycle gates. Do not reject or accept a current M2 candidate using the deferred `1.5 s` absolute-latency gate.
