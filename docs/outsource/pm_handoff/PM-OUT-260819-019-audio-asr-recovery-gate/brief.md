# M4a Audio ASR recovery candidate and real-time hard gate

- **Handoff ID**: `PM-OUT-260819-019-audio-asr-recovery-gate`
- **Related change request**: `CR-AUDIO-M4A-G1B-ASR-SCOPE-001`
- **Status**: `Open — Core ACK required`
- **Milestone**: M4a Gate 1B / Audio POC M2
- **Requestor**: Product Team
- **Decision owner**: Core Designer
- **Committed POC input**: branch `dev_audio_m2`, SHA `b00df085b2817fe9e8cad4faad2cd0fac1c59c69`

## Product decision

The authorized SenseVoice ASR row failed the frozen quality gates: Taiwan-Mandarin
core CER was 41.629% against <=20%, and overall sentence correctness was 6%
against >=70%. Its hot latency p95 (411.204 ms), RTF p95 (0.051401), peak RSS
(374.125 MiB), determinism and lifecycle behavior were not the cause. Preserve
this result as a rejection and do not reopen SenseVoice tuning.

Core is requested to issue a revised exact-row Gate 1B ACK with the following
hard boundaries:

1. The next primary is **faster-whisper `small`, multilingual, CPU `int8`**.
   Core must pin the exact model revision, artifact hashes, license/notice and
   complete aarch64 offline dependency closure before execution.
2. Freeze `cpu_threads=4`, `num_workers=1`, `compute_type=int8`, `beam_size=1`,
   `best_of=1`, `temperature=0`, `language=zh`,
   `condition_on_previous_text=false`, `without_timestamps=true`, and
   `vad_filter=false`. VAD remains a separate bounded-utterance stage.
3. Add a **hard hot final-transcript latency p95 gate of <=1.5 seconds**. Keep
   <=1.0 second as an advisory target. Do not relax RTF p95 <=2.0, core CER
   <=20%, overall sentence correctness >=70%, the 1250 MiB peak-RSS advisory
   ceiling, frozen fixtures or lifecycle gates.
4. Do not include SenseVoice Large in this round. No exact reviewable artifact,
   license and mature aarch64/offline runtime path has been established for it.
5. Keep `asr-whispercpp-base-q5_1-1.9.2` **deferred and non-executable**.
   whisper.cpp may be reconsidered only through a separate exact `small`
   quantized fallback proposal if faster-whisper small is close on quality but
   cannot satisfy latency or memory constraints.

The 4-thread profile and 1.5-second limit are product requirements for real-time
voice response. They apply only to a newly ACKed recovery row and do not rewrite
the completed SenseVoice evidence.

## Required response

Core must return one written disposition:

- `ACCEPTED`: issue the exact faster-whisper small row ACK with the artifact,
  runtime closure, parameters and gates above; or
- `REJECTED`: state that no compliant exact row can be authorized so Audio POC
  can close ASR as an evidence-backed no-go.

Until that response, Audio POC must not build, install, import, load, execute or
benchmark any ASR fallback. This handoff requests no additional Pi testing or
development before the ACK.

## References

- POC request: `poc_audio/deliveries/CR-AUDIO-M4A-G1B-ASR-SCOPE-001.md` at
  `b00df085b2817fe9e8cad4faad2cd0fac1c59c69`
- [faster-whisper README](https://github.com/SYSTRAN/faster-whisper/blob/master/README.md)
- [faster-whisper transcription API](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
- [OpenAI Whisper model sizes](https://github.com/openai/whisper)
- [SenseVoice repository](https://github.com/FunAudioLLM/SenseVoice)
