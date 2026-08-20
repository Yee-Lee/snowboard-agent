# M4a Audio ASR recovery candidate and real-time hard gate

- **Handoff ID**: `PM-OUT-260819-019-audio-asr-recovery-gate`
- **Related change request**: `CR-AUDIO-M4A-G1B-ASR-SCOPE-001`
- **Status**: `Resolved — Core ACK issued; archived`
- **Milestone**: M4a Gate 1B / Audio POC M2
- **Requestor**: Product Team
- **Decision owner**: Core Designer
- **Superseded POC input**: branch `dev_audio_m2`, SHA `b00df085b2817fe9e8cad4faad2cd0fac1c59c69`
- **Revised POC input**: branch `audio`, SHA `ccfc2477a04cd2c53341fabb13a620fd89a51e5a`
- **Core disposition**: `ACCEPTED` in `DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002`

## Product decision

The authorized SenseVoice ASR row failed the frozen quality gates: Taiwan-Mandarin
core CER was 41.629% against <=20%, and overall sentence correctness was 6%
against >=70%. Its hot latency p95 (411.204 ms), RTF p95 (0.051401), peak RSS
(374.125 MiB), determinism and lifecycle behavior were not the cause. Preserve
this result as a rejection and do not reopen SenseVoice tuning.

Core is requested to issue a revised exact-row Gate 1B ACK with the following
hard boundaries:

1. The next primary is **whisper.cpp `1.9.2`, multilingual `small`, Q8_0**.
   Proposed bytes are `ggml-small-q8_0.bin`, 264 MB, SHA-256
   `49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f`.
   Core must pin the immutable model revision, existing exact engine source,
   license/notice and complete CPU-only aarch64 build closure before execution.
2. Pre-authorize the same `small` model in **Q5_1** only as a conditional
   resource/latency fallback. Proposed bytes are `ggml-small-q5_1.bin`, 190 MB,
   SHA-256
   `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`.
   Q5_1 may run only if Q8_0 first passes both frozen quality gates but misses
   the 1.5-second latency gate or exceeds the existing 1250 MiB peak-RSS
   advisory ceiling. If Q8_0 fails quality, stop rather than execute Q5_1.
3. Freeze both rows at four CPU threads, one worker, greedy decoding equivalent
   to `beam_size=1` / `best_of=1`, `temperature=0`, `language=zh`, translation
   disabled, previous-text conditioning disabled, timestamps disabled and
   internal VAD disabled. VAD remains a separate bounded-utterance stage.
4. Add a **hard hot final-transcript latency p95 gate of <=1.5 seconds**. Keep
   <=1.0 second as an advisory target. Do not relax RTF p95 <=2.0, core CER
   <=20%, overall sentence correctness >=70%, the 1250 MiB peak-RSS advisory
   ceiling, frozen fixtures or lifecycle gates.
5. Do not include SenseVoice Large in this round. No exact reviewable artifact,
   license and mature aarch64/offline runtime path has been established for it.
6. Keep `asr-whispercpp-base-q5_1-1.9.2` **deferred and non-executable**. Keep
   faster-whisper `small` multilingual CPU `int8` deferred this round; it is no
   longer the requested recovery primary.

The 4-thread profile and 1.5-second limit are product requirements for real-time
voice response. They apply only to a newly ACKed recovery row and do not rewrite
the completed SenseVoice evidence.

## Required response

Core must return one written disposition:

- `ACCEPTED`: issue exact-row ACKs for whisper.cpp small Q8_0 and the conditional
  Q5_1 fallback with pinned artifacts, source/build closure, execution order,
  parameters and gates above; or
- `REJECTED`: state that no compliant exact row can be authorized so Audio POC
  can close ASR as an evidence-backed no-go.

Until that response, Audio POC must not build, install, import, load, execute or
benchmark any ASR fallback. This handoff requests no additional Pi testing or
development before the ACK.

## References

- POC request: `poc_audio/deliveries/CR-AUDIO-M4A-G1B-ASR-SCOPE-001.md` at
  `ccfc2477a04cd2c53341fabb13a620fd89a51e5a`
- [whisper.cpp README](https://github.com/ggml-org/whisper.cpp/blob/master/README.md)
- [whisper.cpp model files](https://huggingface.co/ggerganov/whisper.cpp/tree/main)
- [OpenAI Whisper model sizes](https://github.com/openai/whisper)
- [SenseVoice repository](https://github.com/FunAudioLLM/SenseVoice)
