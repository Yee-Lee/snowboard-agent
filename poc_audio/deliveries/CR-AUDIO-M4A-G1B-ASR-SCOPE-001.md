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

1. Make **faster-whisper `small`, multilingual, CPU `int8`** the next primary
   ASR candidate. The exact model revision, artifact hashes, license/notice and
   complete aarch64 offline dependency closure must be proposed and ACKed before
   build, install, import, load or execution. Discovery metadata may inform that
   proposal but does not itself authorize execution.
2. Freeze the candidate runtime profile at `cpu_threads=4`, `num_workers=1`,
   `compute_type=int8`, `beam_size=1`, `best_of=1`, `temperature=0`,
   `language=zh`, `condition_on_previous_text=false`,
   `without_timestamps=true`, and `vad_filter=false`. VAD remains a separate
   bounded-utterance stage.
3. Add a **hard hot final-transcript latency p95 gate of <=1.5 seconds**. Keep
   the <=1.0-second target as advisory. Do not relax the existing RTF p95
   <=2.0, Taiwan-Mandarin core CER <=20%, overall sentence correctness >=70%,
   peak-RSS advisory ceiling of 1250 MiB, frozen fixtures or lifecycle gates.
4. Do not authorize another SenseVoice tuning pass. SenseVoice Large is out of
   this round because no exact, reviewable public artifact plus license and
   mature aarch64/offline runtime path has been established for this POC.
5. Keep existing row `asr-whispercpp-base-q5_1-1.9.2` **DEFERRED and not
   executable**. The whisper.cpp engine remains eligible only as a future,
   separately proposed `small` quantized resource fallback if faster-whisper
   small is near the quality gate but misses latency or memory constraints.

The 4-thread change and 1.5-second latency limit are deliberate product
requirements for real-time voice response. They supersede the prior two-thread
ASR comparison profile only for a newly ACKed recovery row; they do not rewrite
or invalidate the completed SenseVoice evidence.

## Required Core response

Core should return one written disposition:

- `ACCEPTED`: issue an exact-row ACK containing the pinned faster-whisper small
  artifact/runtime closure and the profile and gates above; or
- `REJECTED`: state that no compliant exact row can be authorized, allowing the
  POC to close ASR as an evidence-backed no-go.

Until that response, the POC must not execute any ASR fallback. No further Pi
testing is requested by this handoff, and the device may be shut down after this
document is delivered.

## Technical references

- [faster-whisper README](https://github.com/SYSTRAN/faster-whisper/blob/master/README.md)
- [faster-whisper transcription API](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
- [OpenAI Whisper model sizes](https://github.com/openai/whisper)
- [SenseVoice repository](https://github.com/FunAudioLLM/SenseVoice)
