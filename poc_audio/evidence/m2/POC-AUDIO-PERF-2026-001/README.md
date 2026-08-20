# POC-AUDIO-PERF-2026-001 evidence index

Status: `REVIEWED BOUNDED DIAGNOSTIC — Q8 QUALITY NOT ADVANCED`

This packet advances the M2 ASR candidate comparison and rejected-candidate
record. It does not close Gate 2A: the run used frozen VAD labels rather than a
live VAD implementation, used two hot repetitions rather than the formal 20,
and treats absolute final-transcript latency as an observation pending the
requested scope decision.

## Tested identity and method

- Branch: `audio`
- Tested implementation SHA: `fd51a4f36da61fa9af7e210c7dec0170b0cffcbc`
- Candidate: `asr-whispercpp-small-q8_0-1.9.2`
- Model SHA-256:
  `49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f`
- Frozen VAD-label index SHA-256:
  `85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74`
- Source fixture-set SHA-256:
  `6fcde1667a690666e1268e541eea450890d4c437472c908067e3521787749f96`
- Derived manifest SHA-256:
  `62d4840c452962f4d00a2b81aa0ebe07eb6378d73767a34aa18b07e6f6ce156e`

The runner verified all 50 delivered fixture hashes, then derived one 16 kHz
mono S16_LE input per fixture from the first labelled speech start to the last
labelled speech end. Internal pauses were preserved; intervals were not
concatenated and source WAVs were not changed. This is ideal-label-bounded ASR,
not execution evidence for a VAD engine or integrated VAD-to-ASR latency.

Across the 50 derived inputs, duration was 1.74–4.45 s, with 3.13 s median and
3.1866 s mean. Total input duration was 159.33 s; total labelled speech was
145.75 s. The difference is retained internal pause or labelled boundary
context, not synthetic padding.

## Build and thread screening

Both builds used whisper.cpp 1.9.2, Release `-O3 -DNDEBUG`, CPU only, and kept
OpenMP/BLAS/GPU backends off. The only intended build variable was
`GGML_NATIVE`: generic `OFF`, native `ON`. Native compilation selected the
Cortex-A76 path with dot-product and FP16-vector support; i8mm, SVE and SME were
not selected.

The longest bounded input (4.45 s input, 3.51 s labelled speech) was used for
one inference per screening profile:

| Profile | Threads | Latency | Input RTF | Effective cores | Peak RSS | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| generic | 4 | 11.046 s | 2.482 | 3.971 | 551.812 MiB | RTF observation failed |
| native | 1 | 12.662 s | 2.845 | 1.000 | 555.422 MiB | RTF observation failed |
| native | 2 | 6.795 s | 1.527 | 1.997 | 554.906 MiB | RTF observation met |
| native | 4 | 4.031 s | 0.906 | 3.958 | 554.625 MiB | selected |

Native four-thread inference was 2.74x faster than generic four-thread on the
same bounded sample. This ratio isolates the native-build effect; it is not a
VAD-cropping speedup. The historical 11.080 s p95 used complete 6/8-second
inputs and a different suite summary, so it is retained only as a cross-packet
observation. Generic inference still took 11.046 s after bounding the longest
sample to 4.45 s, which gives no evidence that trimming alone materially
reduced absolute inference time in this duration range.

The cross-packet RTF p95 also did not improve: historical full-input generic
RTF was 1.831987, while the new bounded/native result was 1.933469, about 5.5%
higher. Shorter inputs reduce the RTF denominator while fixed inference work
remains. Therefore the lower 4.139 s absolute p95 cannot be presented as an
overall RTF-efficiency gain; only the same-input build screening isolates a
native optimization gain.

The selected profile observed all four cores, four simultaneously active tasks
and 99.504–100% per-core utilization at 2.8 GHz. This demonstrates real
four-core use, while also showing that CPU headroom is essentially exhausted.

## Two-hot-cycle result

The selected native/four-thread profile ran all 50 fixtures for exactly two hot
cycles after three unscored warmups: 100 scored inferences.

| Metric | Result | Diagnostic boundary |
| --- | ---: | --- |
| Controller latency p50 / p95 | 4.042 / 4.139 s | observation only |
| Native inference p50 / p95 | 4.041 / 4.138 s | observation only |
| Input duration median | 3.13 s | range 1.74–4.45 s |
| Input RTF p50 / p95 | 1.307 / 1.933 | p95 <=2.0 met |
| Speech RTF p50 / p95 | 1.402 / 1.933 | reported separately |
| CPU time p50 / p95 | 15.987 / 16.366 s | 3.958 / 3.962 effective cores |
| Peak RSS | 555.438 MiB | below 1250 MiB advisory ceiling |

All 50 fixtures produced the same hypothesis hash in both cycles. CPU0–CPU3
utilization was 99.4–99.794%, frequency stayed at 2.8 GHz, temperature rose
from 35.85 C to 55.65 C, and throttle remained `0x0`.

## Quality and semantic review

Frozen scoring did not pass: overall sentence correctness was 34%, versus the
70% frozen gate. Taiwan-Mandarin core CER improved to 5.429864%, but the
category split shows that this does not make the candidate safe for commands:

| Category | Sentence correctness | CER |
| --- | ---: | ---: |
| Taiwan Mandarin | 70.0% | 5.429864% |
| Code switch | 10.0% | 26.086957% |
| Date | 33.333333% | 11.111111% |
| Number | 0.0% | 41.573034% |
| Product term | 0.0% | 19.402985% |

A private, review-only six-sample spot check retained no transcript in Git.
It confirmed that a simple Mandarin homophone can remain understandable, but
English control terms, numeric nouns, frame terminology and the Raspberry Pi 5
product name can change into different words. An LLM may recover some benign
surface-form variation, but it must not be expected to guess changed command
entities, technical terms or numbers. This review does not alter frozen scores.

## Security, cleanup and retained findings

The measured run used an isolated network namespace and opened no capture or
playback device. No speaker playback occurred, no PCM or raw transcript was
emitted to the report, and final cleanup reported zero children, threads,
streams, iterators and device owners. The post-run Pi checkout was clean at the
tested detached SHA; no worker or runner remained, and throttle was `0x0`.

The first attempt at submitted SHA
`5964d9683b538acd37e11197e60cbe4640ff604d` stopped before model load because
the runner expected an obsolete label-index shape. No inference result was
produced. The finding is retained; parser support was appended in the tested
SHA rather than rewriting the submitted candidate.

Raw reports remain outside Git in controlled packet `20260820T104500Z`:

| Report | SHA-256 |
| --- | --- |
| `generic-build-fd51a4f.json` | `3fc9455c66e8d04a3a87ea4932e51942b89e595f590ed4db868070d382739101` |
| `native-build-fd51a4f.json` | `465f3b9fb76c4886ad678507bbb93d4d07aeae9a4d652630ac8f450673011088` |
| `screen-generic4-fd51a4f.json` | `d9078651b0ed19547eb9f5ec410b9b43efb999cd393cf44347fc47e24e56eaad` |
| `screen-native1-fd51a4f.json` | `307f91520760b154398b2a51991122ecb35ce9af2e60c6fc48ae9cd681f41522` |
| `screen-native2-fd51a4f.json` | `12eec1cac99cd43ed0fb2a0057c192b645276c62454401e9a5c85c1675ee13ba` |
| `screen-native4-fd51a4f.json` | `ced1b799f28532a412a679784de1b207a2f3a6afbcc1e0f19401d7ea49a19812` |
| `q8-bounded-native4-twohot-fd51a4f.json` | `8ea8ae6b3b724810be8439a7eb7572910e1a822444848eea6b709796ee47fd43` |

## Disposition and reusable low-cost screen

Q8 now has a credible CPU result: native compilation and four threads recover
substantial speed, and the bounded run meets the diagnostic RTF boundary. It
is not advanced because frozen overall quality fails and absolute latency
remains about four seconds even with all cores occupied. Product/Core must
decide the requested absolute-latency scope and the next exact model row.

For another authorized model, reuse the same bounded fixtures and native
four-thread method. First load it once, transcribe the six representative Q8
semantic failures once each, and run the longest bounded fixture once for
latency/RSS. Stop if key entities do not improve. Only a clear quality step
change justifies the 50-fixture x two-hot-cycle diagnostic. Medium is the next
quality-probe recommendation, but remains prohibited until an exact quantized
artifact row is authorized; Q5/base/HAT remain deferred.

Additional untested levers are explicitly not part of this result. A
same-sample flash-attention or OpenBLAS A/B could cheaply test latency/RSS, but
neither is expected to change recognition quality and native Q8 already uses
optimized ARM repack kernels. OpenMP is lower priority because the internal
thread pool already saturates all four cores. Initial prompts/domain vocabulary
could target technical terms but change the frozen decoding configuration and
may introduce biased guesses; streaming changes the pipeline and perceived
latency rather than model RTF. HAT requires a separate accelerator model/backend
path. All require a newly authorized test row; threads above four and more
aggressive speech-interval concatenation are not recommended.
