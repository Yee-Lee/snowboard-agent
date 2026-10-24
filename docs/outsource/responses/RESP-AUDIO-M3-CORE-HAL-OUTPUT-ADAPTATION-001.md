# RESP-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001

**Date**: 2026-08-23
**Role**: Core Designer
**Target**: `CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001`
**Status**: `ACCEPTED — IMPLEMENTATION IN PROGRESS`

---

## 1. Core ownership of output adaptation

**Accepted.** Core AudioOutput HAL owns the explicit 16 kHz / mono / S16_LE →
48 kHz / stereo / S32_LE adaptation. Audio POC TTS (Matcha 1.13.5) remains a
native 16 kHz mono producer and must not resample, expand channels or change
container. No POC-side conversion layer is authorized.

---

## 2. Public / native output configuration

The following configuration contract is adopted:

- `audio.output.stream_format`: 16,000 Hz, 1 channel (mono), S16_LE.
  This is the format `AudioOutput.play()` accepts from TTS.
- `audio.output.native_format`: 48,000 Hz, 2 channels (stereo), S32_LE.
  This is the format delivered to the ALSA `hw:` device.

`AudioOutput.play()` accepts ordered legal chunks in **stream format** and
consumes the complete iterator or returns one explicit bounded error. All
conversion is internal to Core AudioOutput and invisible to TTS/Speak.

---

## 3. Implementation plan

Core Developer will deliver the following in a single implementation commit:

### 3.1 New module: `src/sbd/core/audio/alsa/adaptation.py`

`StreamFormatAdapter` — stateful converter: stream_format → native_format.

- **Resampler**: `samplerate==0.2.4` `sinc_best` (already in `dev` and
  `rpi-audio` dependencies). Ratio = 48000/16000 = 3.0. Resampler state is
  preserved across calls to `convert()` within a session.
- **Channel expansion**: mono → stereo by duplicating the single channel.
- **Sample format**: S16_LE → S32_LE by scaling: `s32 = s16 * 65536`
  (equivalent to a left-shift of 16 bits into the signed 32-bit range,
  no clipping possible).
- **Chunk boundary invariant**: output samples depend only on accumulated
  input, not on where chunk boundaries fall.
- **End-of-input flush**: `flush()` drains any resampler tail and returns
  the remaining converted frames.
- **Session reset**: `reset()` discards resampler state; called between
  independent `play()` invocations.

### 3.2 Modified: `src/sbd/core/audio/alsa/output.py`

- On `start()`: if `config.output.stream_format != config.output.native_format`,
  instantiate `StreamFormatAdapter`; otherwise run in passthrough mode.
- `play()`:
  - Validate each incoming chunk as a multiple of **stream** frame bytes
    (2 bytes for S16_LE mono), not native frame bytes.
  - Pass chunk through adapter; write resulting native bytes to ALSA.
  - After iterator exhaustion, call `adapter.flush()` and write residue.
- On `stop()`, `cancel`, `force-abort`, `reopen`: call `adapter.reset()`.
- `_NATIVE_FRAME_BYTES` (8) remains the ALSA write unit; stream frame bytes
  become a separate constant `_STREAM_FRAME_BYTES = 2`.

### 3.3 Config validation

- Strict validator must reject a config where `stream_format` and
  `native_format` are both non-None but the conversion path is not the
  single supported route (16kHz/mono/S16_LE → 48kHz/stereo/S32_LE).
- `native_format=None` in `AudioOutputConfig` is interpreted as passthrough
  (stream_format == native_format).

### 3.4 New tests (portable, no rpi marker)

Seven test groups to be added to `tests/test_m3_aud_001_002_003_004.py`
or a new `tests/test_m3_audo_001_002_003_004_005_006_007.py`:

1. **Deterministic conversion**: fixed 16 kHz mono S16_LE fixture (sine,
   silence, impulse) → verify output sample count, channel count, container.
2. **Chunking byte-equivalence**: same input split at 1, 2, 3, 7, and
   aligned boundaries must produce bit-identical output.
3. **Input/output accounting**: every input sample is consumed; output
   frame count equals `ceil(input_samples * 3.0)` within resampler tolerance;
   stereo duplication and S32_LE scaling correct.
4. **Impulse/onset and tail**: leading impulse appears in output without
   pre-delay truncation; trailing non-zero samples not dropped after flush.
5. **Lifecycle and cleanup**: success, invalid-device, write-error, cancel,
   force-abort and five-reopen cycles all produce zero final resource delta;
   each reopen produces a fresh adapter with empty state.
6. **Config validation**: strict config correctly separates stream vs native;
   unsupported conversion route is rejected at construction.
7. **Regression**: existing `_alsa_config()` passthrough path (stream == native)
   continues to behave identically to current `output.py`; ALSA device
   negotiation (48kHz/stereo/S32_LE/period960) is unchanged.

---

## 4. Distinct identity confirmation

| Identity | SHA |
| --- | --- |
| Audio POC Option A validation | `de3b0bab4daaf47f62956d4b27f6697b3d4fa823` |
| Superseded Core HAL implementation (M3 accepted) | `5c9e5aac47e7f4f0dd168d8c75541438ee74f858` |
| New Core HAL with output adaptation | `PENDING — Developer implementation` |

The existing M3 acceptance commit `2fb2e18f934c3d06392074adba3c4518402101e9` /
tag `core_m3` remains historical acceptance evidence and is not modified.

The new AudioOutput change is an **M3 HAL append-only revision** on the `core`
branch. It does not reopen M3 milestone scope; it closes a contract gap that
blocked POC M3 hardware qualification. The authoritative ACK commit is the
new implementation SHA on `core` that this response will deliver.

---

## 5. Remaining blockers to Audio POC M3 packet sign-off

1. Core Developer implements adaptation + tests per §3 above.
2. Core tests pass portable matrix.
3. Core Designer code review confirms design alignment.
4. New Core SHA committed and delivered to Audio POC `pm_handoff/`.
5. Audio POC updates M3 test packet with the new Core SHA and corrects
   the identity table.
6. Core Designer signs off the corrected M3 test packet.

Pi evidence (Core Pi playback through MAX98357A VoiceHAT with Matcha risk
prompt set) remains Audio POC M3 evidence as stated in the CR; Core will
provide a tone-only sanity playback regression on Pi as part of the rpi
test suite, but User listening of the Matcha prompts is not replaced.

---

## 6. M4A-P9 is not an M3 hardware-qualification entry gate

**Confirmed.** M4A-P9 (M4b resource reservation) is a parallel dependency
on Core/LLM input. It does not block M3 qualification preparation, this
AudioOutput correction, or M3 packet sign-off.
