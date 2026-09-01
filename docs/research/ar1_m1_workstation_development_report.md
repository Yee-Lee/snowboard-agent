# AR1M1 Workstation Development Report

Status: `DRAFT / NON-FORMAL X86 WORKSTATION DEVELOPMENT EVIDENCE / NOT PI 5`

Date: 2026-09-01

This report records engineering bring-up, not a score, ranking, Pi hardware
disposition, qualification decision, or final outcome. The measurements below
are single-run diagnostics from a development worktree. They must be repeated
from a clean immutable SHA before they can become reviewed M1 evidence, and
workstation results cannot replace Pi 5 smoke or formal comparison.

## Execution environment — explicitly not Raspberry Pi 5

Every measurement in this report was produced in a virtualized x86 workstation
feasibility environment:

- Ubuntu 24.04.4 LTS;
- x86_64 virtual CPU architecture with a hypervisor-present Haswell profile;
- exactly 2 online vCPUs, affinity CPUs 0–1, one thread per virtual core;
- CPU-only execution with no GPU acceleration; and
- x86_64 runtime binaries and wheels, not aarch64 artifacts.

This environment does **not** emulate Raspberry Pi 5 CPU microarchitecture,
memory bandwidth, aarch64 runtime behavior, thermal limits, throttling, or the
approximately 1 GB product ASR allocation. The results answer only whether the
development paths function and what bottlenecks appear under an x86 2-vCPU
Ubuntu 24.04 simulation. They are not Pi 5 measurements and must never be
reported as target-hardware performance.

## What was measured

All five exact artifacts were verified before model load and exercised through
their native backend API and the common thin adapter. The frozen input is
`asr-clear-002-p0`: 2.66 seconds of authorized Taiwan Mandarin speech cropped
from the human-reviewed 470–3130 ms source interval. The derived speech start
is 0 ms and speech end is 2660 ms.

The timing dimensions are intentionally separate:

- **TTFT** is the paced, application-observable delay from frozen speech start
  to the first non-empty changed partial returned by the adapter. Model load
  and session creation occur before its clock starts.
- **Full-utterance RTF** is unpaced resident-model decode wall time divided by
  2.66 seconds. It measures throughput and excludes model load.
- **Speech-end-to-final** is measured on the paced stream from frozen speech
  end to the returned final. It includes endpoint and outstanding decode work.
- **Cold load** is reported separately because it affects process start and
  recovery but is not a per-utterance cost while the model remains resident.

Process-tree RSS/PSS, threads, CPU time, effective cores, per-chunk call time,
and delivery lateness were sampled by the supervising process. The
1,000,000,000-byte RSS value is an observation reference, not an elimination
rule. Transcript content and raw output remain outside Git; only hashes and
sanitized aggregates are retained.

## X86 2-vCPU diagnostic observations

| Probe order | Candidate | Native load (s) | Full decode (s) | Full RTF | TTFT (ms) | Speech-end → final (ms) | Native decode cores | Paced deadline misses / 17 | Paced peak RSS |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Zipformer x-large INT8 | 76.16 | 6.40 | 2.405 | 2,833 | 4,183 | 1.50 | 15 | 1,080,000,512 B |
| 2 | WeNet WenetSpeech CTC INT8 | 3.56 | 1.03 | 0.387 | 1,129 | 92 | 1.55 | 7 | 249,892,864 B |
| 3 | Nemotron 3.5 Q8_0 | 0.45 | 27.83 | 10.461 | 10,813 | 22,574 | 0.93 | 15 | 998,588,416 B |
| 4 | Zipformer large INT8 | 38.97 | 4.57 | 1.718 | 993 | 170 | 1.15 | 14 | 295,137,280 B |
| 5 | WeNet AISHELL CTC INT8 | 2.39 | 0.45 | 0.168 | 763 | 10 | 1.57 | 2 | 145,231,872 B |

These values are not Pi 5 results and do not measure recognition quality. The
table uses the latest matching diagnostic where a path was rerun; observed
run-to-run variance, especially for Nemotron and cold load, is another reason
the clean-SHA packet requires repeats. A single known regression utterance only
proves that each exact runtime can load, accept streaming PCM,
emit partials and a non-empty final, and shut down. Differences between native
and paced load observations also show that one cold-load number is not stable
enough to extrapolate to Pi 5.

## Candidate breakdown

### Zipformer x-large INT8

The exact large ONNX closure works through sherpa-onnx and uses more than the
RSS reference in the paced process tree. Cold initialization consumed roughly
one effective core and took tens of seconds. Resident decode used about 1.5
cores but still had RTF 2.405; the paced run accumulated 15 deadline misses,
and its 2.8-second TTFT was followed by more than four seconds of
speech-end-to-final delay.

The experiment remains valuable even if no M2 budget is assigned. It proves
that artifact size alone understates the process memory closure, identifies a
single-core-heavy initialization path, and establishes that INT8 does not by
itself make this model real-time on the current CPU environment. It also gives
a functioning upper-capacity reference for runtime and adapter behavior.

### WeNet WenetSpeech streaming CTC INT8

This row has a much smaller operational closure: roughly 250 MB peak RSS,
seconds rather than tens of seconds to load, and full-utterance RTF below one.
Its first partial appeared from the 640 ms audio chunk and was observable at
about 1.13 seconds. Seven paced deadline misses and a 487 ms maximum chunk call
show bursty decode work even though the utterance recovered to a 92 ms
speech-end-to-final delay.

This is a credible low-cost path for later quality investigation, but the M1
runtime is sherpa-onnx online CTC. It does not prove native WeNet U2++ attention
rescoring, and the one smoke sentence cannot establish WenetSpeech quality for
Taiwan Mandarin or English entities.

### Nemotron 3.5 Q8_0

The portable C ABI and Q8_0 artifact load quickly, but inference is the limiting
stage. Decode used only about 0.92–0.93 effective core, and repeated development
runs placed full-utterance RTF from about 8.7 to 10.5. The latest fail-closed
native-final run recorded RTF 10.461. TTFT exceeded ten seconds, and the paced
stream accumulated more than 18
seconds of delivery backlog. Peak RSS sat immediately below the reference,
leaving effectively no safe product headroom under an approximately 1 GB ASR
allowance.

This row remains valuable even if it receives no CPU-only M2 spending. It
separates fast GGUF mapping from slow decoder execution, proves stable stream
ownership through the native C ABI, and demonstrates that portable INT8/Q8
packaging is not equivalent to CPU real-time feasibility. Earlier one- versus
two-CPU diagnostics also showed no useful scaling on this workstation, so a
GPU-oriented or materially different optimized runtime would be a new path,
not an interpretation change to this result.

### Zipformer large INT8

The large model reduced peak RSS to roughly 295 MB and produced a first partial
in about one second, but cold load still took tens of seconds. Native
full-utterance RTF remained above one. The paced stream finished close to audio
duration by using more parallel CPU during parts of the run, yet 14 deadline
misses and approximately 350 ms maximum delivery lateness expose uneven chunk
cost rather than consistently bounded streaming work.

This row is technically more reachable than x-large but remains conditional:
Pi CPU scheduling, repeat variance, quality, and bounded thread/context probes
would have to justify additional cost. M1 has already identified the useful
trade-off boundary—moderate resident memory and acceptable first partial do not
guarantee sustained full-sentence throughput or cheap process recovery.

### WeNet AISHELL streaming CTC INT8

This is the smallest operational row in the current set. It loaded in a few
seconds, stayed near 145 MB RSS, used about 1.57 cores during unpaced decode,
and the latest native-final run recorded RTF 0.168. Its TTFT was about 763 ms,
only two chunks exceeded the
strict 5 ms delivery tolerance, and speech-end-to-final was about 10 ms.

The engineering surface is therefore inexpensive enough for broader quality
testing. That is not a quality conclusion: AISHELL domain/language coverage may
be less aligned with the product, and the current smoke cannot measure intent,
English entities, code-switch, volume, or speech-in-noise behavior.

## Lifecycle and offline breakdown

Every candidate completed the development lifecycle path with one resident
model: two isolated sessions, reset without reload, typed cancel, terminal
cancel behavior, recovery, typed out-of-order and unknown-session errors,
top-one fallback, non-empty partial/final events, stream cleanup, and bounded
shutdown. The adapter closes native stream ownership once on final, reset,
cancel, error recovery, and shutdown.

Each exact candidate also completed a syscall-level offline audit under local
pre-acquired artifacts. The successful traces contained zero attempted network
syscalls. Failed diagnostic attempts were preserved rather than overwritten.
This proves the tested execution closure was offline; the class name
`OnlineRecognizer` refers to streaming recognition and does not imply an
Internet service.

## Post-process and endpoint research

The selected adapter paths currently expose top-one fallback only, with no
confidence and no stable token timestamps. A genuine second-pass scorer cannot
recover hypotheses that the first-pass runtime never exports. The WeNet rows
also do not expose their native attention-rescoring path through the tested
sherpa conversion.

The dependency-free diagnostic scaffold proves four boundaries without
changing the final transcript:

- caller-labelled fake VAD speech-start/speech-end, reset, and cancel flow;
- final-only fake scoring and rejection of partial input;
- top-one fallback and synthetic N-best selection using only transcript hashes;
- an invariant that downstream final text remains unchanged.

Potential M2 diagnostics are deterministic raw-versus-normalized text scoring,
audited English-entity/context experiments, a separate bounded endpoint study,
and true N-best rescoring only if a different runtime surface exposes genuine
alternatives, scores, and timing. No real post-process component receives
formal comparison credit or enters AR1M3.

## Draft M2 research-spend interpretation

This is a proposal for User review, not a frozen advance decision:

- WeNet WenetSpeech and WeNet AISHELL have the clearest workstation engineering
  path for broader quality evidence.
- Zipformer large is conditional on whether a bounded Pi smoke or thread/context
  probe can justify its cold-load and sustained-throughput cost.
- Zipformer x-large and Nemotron preserve important M1 evidence, but the current
  CPU/RSS observations do not support spending M2 comparison effort without a
  materially different runtime or hardware hypothesis.

Not entering M2 does not make an M1 experiment wasted. The stopped research
rows define resource cliffs, isolate runtime limitations, validate cleanup and
offline closure, and prevent later teams from repeating expensive paths under
the false assumption that model quantization or a successful three-second
transcript implies product feasibility.

## Remaining before reviewed M1 evidence

- Commit a complete reviewable development segment, then repeat critical
  preflight, native, adapter, lifecycle, TTFT/RTF, offline, timeout, cleanup,
  and telemetry checks from that clean immutable SHA.
- Close the documented fixture coverage gaps for intent taxonomy, English
  entities, volume conditions, and speech in noise. Role and holdout freeze
  still requires User review.
- Run the same-SHA critical smoke and lifecycle packet on a real Pi 5 to
  establish
  aarch64, CPU-only resource, thermal/throttling, and hardware behavior.
- Keep all current values non-formal until evidence review; workstation results
  never substitute for Pi formal scoring or integrated qualification.
