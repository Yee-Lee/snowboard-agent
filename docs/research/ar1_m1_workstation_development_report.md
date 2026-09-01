# AR1M1 Workstation Development Report

Status: `FINAL / NON-FORMAL X86 WORKSTATION DEVELOPMENT EVIDENCE / NOT PI 5`

Date: 2026-09-01

This report records engineering bring-up, not a score, ranking, Pi hardware
disposition, qualification decision, or final outcome. The five-row workstation
packet has now been repeated from clean immutable SHAs. Its measurements remain
single-run, non-formal development diagnostics, and workstation results cannot
replace Pi 5 smoke or formal comparison.

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

## Clean-SHA workstation verification

The runtime harness and five exact native candidates were verified from clean
SHA `f478f4baab39c99c361e63bb9d956f09384efecc`. A strict offline-audit parser
incorrectly treated `strace` signal metadata as a network syscall; the failed
attempt was preserved, the parser was fixed without changing a model runtime,
and all offline/lifecycle cases were verified from clean append-only SHA
`55c28ab0eef50ba41dbee1ac1abc6a162f2bb2a6`.

At those SHAs:

- exact artifact, dependency, fixture, runtime, and unloaded-model preflights
  passed for all five rows;
- all five native probes returned non-empty sanitized finals;
- all five paced adapter children completed under syscall-level offline audit,
  and every successful network trace was empty;
- every candidate passed all 14 lifecycle assertions for isolation, reset,
  cancel, typed errors, recovery, final/fallback behavior, cleanup, and bounded
  shutdown; and
- 64 repository tests, bytecode compilation, data-safety checks, M0 readiness,
  M1 clean-tree readiness, and a relocated-checkout test passed.

Two unsuccessful attempts remain documented rather than being erased. The
first was the `SIGCHLD` metadata false positive above. The second was an
operator filename typo for the Nemotron artifact; it produced no network trace
and was repeated once with the frozen exact filename. Neither failure was a
model-performance failure, and no additional model rerun is pending.

## X86 2-vCPU diagnostic observations

| Probe order | Candidate | Native load (s) | Full decode (s) | Full RTF | TTFT (ms) | Speech-end → final (ms) | Native decode cores | Paced deadline misses / 17 | Paced peak RSS |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Zipformer x-large INT8 | 65.13 | 5.88 | 2.209 | 2,833 | 4,183 | 1.46 | 15 | 1,080,000,512 B |
| 2 | WeNet WenetSpeech CTC INT8 | 2.94 | 1.09 | 0.409 | 1,129 | 92 | 1.57 | 7 | 249,892,864 B |
| 3 | Nemotron 3.5 Q8_0 | 0.27 | 25.00 | 9.399 | 10,813 | 22,574 | 0.89 | 15 | 998,588,416 B |
| 4 | Zipformer large INT8 | 33.06 | 2.84 | 1.067 | 993 | 170 | 1.57 | 14 | 295,137,280 B |
| 5 | WeNet AISHELL CTC INT8 | 2.48 | 0.58 | 0.220 | 763 | 10 | 1.56 | 2 | 145,231,872 B |

These values are not Pi 5 results and do not measure recognition quality. The
native load, full decode, full RTF, and native-core columns are clean-SHA
observations. The paced TTFT, speech-end, deadline-miss, and paced-RSS columns
remain the earlier explicit development observations because the clean offline
wrapper retained only a sanitized child-output hash; the report does not infer
timings from that hash. A single known regression utterance only proves that
each exact runtime can load, accept streaming PCM,
emit partials and a non-empty final, and shut down. Differences between native
and paced load observations also show that one cold-load number is not stable
enough to extrapolate to Pi 5.

## Candidate breakdown

### Zipformer x-large INT8

The exact large ONNX closure works through sherpa-onnx and uses more than the
RSS reference in the paced process tree. Cold initialization consumed roughly
one effective core and took tens of seconds. Resident decode used about 1.5
cores but still had RTF 2.209; the paced run accumulated 15 deadline misses,
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
runs placed full-utterance RTF from about 8.7 to 10.5. The clean fail-closed
native-final run recorded RTF 9.399. TTFT exceeded ten seconds, and the paced
stream accumulated more than 18 seconds of delivery backlog. Peak RSS sat
immediately below the reference,
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
full-utterance RTF remained slightly above one. The paced stream finished close
to audio duration by using more parallel CPU during parts of the run, yet 14 deadline
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
and the clean native-final run recorded RTF 0.220. Its TTFT was about 763 ms,
only two chunks exceeded the strict 5 ms delivery tolerance, and
speech-end-to-final was about 10 ms.

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

## Handoff to M2 entry

- No further workstation model rerun is planned unless runtime or measurement
  code changes or review identifies a defect.
- At M2 entry, close the documented fixture coverage gaps for intent taxonomy,
  English entities, volume conditions, and speech in noise. Role and holdout
  freeze still requires User review before formal execution.
- Before formal scoring, run the critical smoke and lifecycle packet at an
  immutable delivery SHA on a real Pi 5 to establish aarch64, CPU-only resource,
  thermal/throttling, and hardware behavior.
- Keep all current values non-formal until evidence review; workstation results
  never substitute for Pi formal scoring or integrated qualification.

The User approved this scheduling boundary and AR1M1 closure on 2026-09-01.
