# PM change request: ASR diagnostic scope after small Q8 signal

- **Change request ID**: `CR-AUDIO-M4A-G1B-ASR-DIAGNOSTIC-SCOPE-002`
- **Status**: `REQUESTED — PENDING PRODUCT / CORE DECISION`
- **Related ACK**: `DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002`
- **Requestor**: Product Team
- **Decision owner**: Core Designer
- **POC owner after ACK**: Audio POC Technical Lead

## Trigger and unchanged evidence

The authorized whisper.cpp multilingual small Q8_0 two-cycle partial diagnostic
on Raspberry Pi 5 observed 9.502262% Taiwan-Mandarin core CER, 28% overall
sentence correctness, 11.080 s hot p95 final-transcript latency, RTF p95
1.831987, and 554 MiB peak RSS. It is gate-ineligible, but provides a strong
quality and real-time no-go signal. A separate controlled semantic review found
26/50 directly usable outputs, 12/50 contextual-only outputs, and 12/50
unsafe-to-guess outputs; raw pairs are external controlled evidence only.

The User directs that the interrupted small-Q8 20-repetition formal
qualification must not resume. This does not erase its incomplete status,
relax a frozen gate, make Q8 pass, or unlock Q5 under the current ACK.
For a potential no-HAT path, the User permits a quality trade-off to be
investigated but does not permit a material latency trade-off: the existing
hot final-transcript p95 <=1.5 s hard boundary remains the decision criterion.
No quality threshold is changed by this request; a later product decision would
be required before selecting a lower-quality fallback.

## Requested diagnostic authorization

Core is requested to replace only the remaining ASR execution order with the
following explicitly gate-ineligible diagnostics. Core must return exact-row
acceptance before any artifact download, build, or Pi execution.

1. Permit the already pinned `asr-whispercpp-small-q5_1-1.9.2` row to run
   **three complete hot fixture cycles** after bounded unscored warm-up. The
   purpose is a CPU-only no-HAT latency/resource trade-off observation, not a
   quality fallback or Gate 2A qualification. Keep four threads, one worker,
   greedy `zh` profile, frozen fixture/scorer, offline boundary, timeout and
   lifecycle checks. Report CER, sentence correctness, latency, RTF, RSS,
   thermal, determinism and cleanup; do not change any threshold or claim a
   pass even if one metric improves.
2. Permit `asr-whispercpp-base-q5_1-1.9.2` to run **three complete hot fixture
   cycles** after the same bounded unscored warm-up. Bind the previously
   proposed multilingual `ggml-base-q5_1.bin` identity: 59,707,625 bytes and
   SHA-256 `422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898`.
   This is also a CPU-only no-HAT speed/quality diagnostic, using the identical
   profile, fixture/scorer, offline, lifecycle and report requirements. It is
   not a small-model fallback, formal qualification, or Gate 2A claim.
3. Permit one **diagnostic-only** whisper.cpp 1.9.2 multilingual medium Q8_0
   hot fixture cycle on the same Pi, after Core binds its immutable model
   repository revision, filename, byte size, SHA-256, notices/license and
   CPU-only aarch64 build closure. Apply the same profile and report fields as
   Q5. This run asks whether a larger Whisper model materially improves quality
   and what single-worker RAM it consumes; it is not expected to establish
   real-time CPU-only viability and does not replace the frozen gate. It is a
   quality/RSS upper-bound observation for a possible later HAT route.

For all three diagnostics, report the observed latency against the unchanged
1.5-second p95 boundary. A no-HAT candidate that exceeds it cannot advance on
the basis of a quality improvement alone.

No further small-Q8 formal repetitions are requested. No microphone capture,
speaker playback, prompt/post-processing change, model tuning, new scorer, or
network-enabled inference is permitted.

## AI HAT follow-up boundary

If medium quality is materially better, Product Team may separately investigate
AI HAT+ 2 procurement and vendor support for a deployable medium ASR artifact.
An AI HAT does not accelerate the existing GGML model by itself; it needs a
Hailo-compatible, immutable artifact and offline aarch64 runtime closure. No
HAT candidate, performance claim, or purchase decision is authorized by this
request. Public material currently demonstrates Hailo Whisper Small, not a
bound medium artifact for this POC.

## Required Core response

Core should return one written disposition:

- `ACCEPTED`: bind the exact small-Q5, base-Q5 and/or medium-Q8 diagnostic row,
  profile, maximum repetitions and evidence requirements; or
- `REJECTED`: retain ACK-002 execution prohibition, allowing the POC to report
  the CPU-only small-Q8 evidence as the current ASR no-go signal.

Until that response, small Q8 remains the only authorized ASR primary; small
Q5, base Q5, medium and HAT remain non-executable, and all frozen gates remain
unchanged.

## References

- [Q8 partial diagnostic evidence](../evidence/m2/M4A-G1B-ASR-RECOVERY-Q8-PARTIAL-001.md)
- [Raspberry Pi AI HAT documentation](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)
- [Hailo Whisper Small model entry](https://hailo.ai/products/hailo-software/model-explorer/generative-ai/whisper-small/)
- [whisper.cpp model catalogue](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md)
