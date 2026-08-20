# PM change request: Gate 1B ASR recovery scope and real-time hard gate

- **Change request ID**: `CR-AUDIO-M4A-G1B-ASR-SCOPE-001`
- **Related ACK**: `DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`
- **Status**: `OPEN — CORE ACK REQUIRED`
- **Requestor**: Product Team
- **Decision owner**: Core Designer
- **POC owner after ACK**: Audio POC Technical Lead

## Trigger evidence

The only authorized ASR execution row,
`asr-sherpa-sensevoice-int8-2025-09-09`, completed all frozen full-fixture
repetitions at POC SHA
`63c2cc179bb3c2525201da0f7a78d2c50b63d759`. Reviewed evidence
[`M4A-G1B-WP3-FULL-QUALIFICATION-001`](../evidence/m2/M4A-G1B-WP3-FULL-QUALIFICATION-001.md)
records Taiwan-Mandarin core CER 41.629% against the <=20% hard gate and 6%
overall sentence correctness against the >=70% hard gate. Hot latency p95 was
411.204 ms, RTF p95 was 0.051401, peak RSS was 374.125 MiB, and all 20 hot
cycles reproduced one stable hypothesis hash per fixture. This is a quality
failure, not a performance or lifecycle failure.

SenseVoice is rejected. The result and frozen fixtures remain unchanged; no
normalization, threshold or post-processing change may be used to make it pass.

## Product decision and requested ACK

Core is requested to revise the Gate 1B execution authorization as follows:

1. Make **whisper.cpp `1.9.2`, multilingual `small`, Q8_0** the next primary ASR
   candidate. Proposed model bytes are `ggml-small-q8_0.bin`, 264 MB, SHA-256
   `49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f`.
   Core must bind an immutable model-repository revision, the existing exact
   whisper.cpp source revision, license/notice and complete CPU-only aarch64
   build closure before execution.
2. Pre-authorize **the same engine and multilingual `small` model in Q5_1** only
   as a conditional resource/latency fallback. Proposed bytes are
   `ggml-small-q5_1.bin`, 190 MB, SHA-256
   `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`.
   Q5_1 may run only if Q8_0 first passes both frozen quality gates but misses
   the 1.5-second latency gate or exceeds the existing 1250 MiB peak-RSS
   advisory ceiling. If Q8_0 fails quality, stop rather than try the more
   compressed row.
3. Freeze both rows at four CPU threads, one worker, greedy decoding equivalent
   to `beam_size=1` / `best_of=1`, `temperature=0`, `language=zh`, translation
   disabled, previous-text conditioning disabled, timestamps disabled and
   internal VAD disabled. VAD remains a separate bounded-utterance stage.
4. Add a **hard hot final-transcript latency p95 gate of <=1.5 seconds**. Keep
   the <=1.0-second target as advisory. Do not relax the existing RTF p95
   <=2.0, Taiwan-Mandarin core CER <=20%, overall sentence correctness >=70%,
   peak-RSS advisory ceiling of 1250 MiB, frozen fixtures or lifecycle gates.
5. Do not authorize another SenseVoice tuning pass. SenseVoice Large is out of
   this round because no exact, reviewable public artifact plus license and
   mature aarch64/offline runtime path has been established for this POC.
6. Keep existing row `asr-whispercpp-base-q5_1-1.9.2` **DEFERRED and not
   executable**. Also keep faster-whisper `small` multilingual CPU `int8`
   deferred this round; it is no longer the requested recovery primary.

The 4-thread change and 1.5-second latency limit are deliberate product
requirements for real-time voice response. They supersede the prior two-thread
ASR comparison profile only for a newly ACKed recovery row; they do not rewrite
or invalidate the completed SenseVoice evidence.

## Required Core response

Core should return one written disposition:

- `ACCEPTED`: issue exact-row ACKs for whisper.cpp small Q8_0 and the conditional
  Q5_1 fallback, including their pinned artifacts, source/build closure,
  execution order, profile and gates above; or
- `REJECTED`: state that no compliant exact row can be authorized, allowing the
  POC to close ASR as an evidence-backed no-go.

Until that response, the POC must not execute any ASR fallback. No further Pi
testing is requested by this handoff, and the device may be shut down after this
document is delivered.

## Technical references

- [whisper.cpp README](https://github.com/ggml-org/whisper.cpp/blob/master/README.md)
- [whisper.cpp model files](https://huggingface.co/ggerganov/whisper.cpp/tree/main)
- [OpenAI Whisper model sizes](https://github.com/openai/whisper)
- [SenseVoice repository](https://github.com/FunAudioLLM/SenseVoice)
