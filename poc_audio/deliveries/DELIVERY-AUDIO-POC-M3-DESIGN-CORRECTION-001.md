# POC Audio → Core Team: M3 Audio Format Design Correction

Delivery ID：`DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001`
狀態：`CORE DIRECTION ACCEPTED / P4 VALIDATION REQUIRED`
日期：2026-08-08
提供方：Audio POC / User as Designer
接收方：Core Team Designer

## 1. Decision requested

The User/Designer approves Option A in `CR-AUDIO-M3-PCM-001` and asks Core Team
to incorporate explicit device-to-stream format adaptation into the Core M3
Audio HAL design. Core Team must accept or reject this correction before the
POC closes the M1 change request.

This correction preserves the external AudioInput stream contract while making
the real hardware boundary explicit and testable. It does not authorize hidden
`plughw:` conversion or conversion inside Listen, VAD, or ASR wrappers.

## 2. Evidence and cause

`M1-NATIVE-AUDIO-001`, measured on the target Pi and hardware at full SHA
`0edeb7d9f8ff3811d1480ab4b464db2842978233`, proves:

| Capability | Reviewed result |
| --- | --- |
| Direct ALSA capture/playback | 48 kHz, stereo, S32_LE only |
| Requested 16 kHz or 44.1 kHz S32_LE | ALSA changes the actual rate to 48 kHz |
| Mono, S16_LE or S24_LE | unavailable through direct `hw:` |
| Reopen | capture 3/3 and playback 3/3 pass |
| Shared-clock concurrent at native format | pass |
| xrun text, device owner after test, throttling | none |

The existing logical AudioInput contract is 16 kHz, mono, S16_LE, 20 ms. The
hardware works, but it cannot provide that contract natively. P2 device/config
evidence is closed; P1 remains a recorded failure resolved only through this
design decision.

## 3. Required contract semantics

Core Team may retain the existing Protocol method signatures:

```python
class AudioInput(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def frames(self) -> AsyncIterator[bytes]: ...
```

The authoritative contract must additionally state:

1. `frames()` yields the configured delivered stream format; that format may
   differ from the native device format only through an explicit HAL-owned
   adaptation configured and validated at startup.
2. For this target, the real backend opens 48 kHz stereo S32_LE and delivers
   16 kHz mono S16_LE in exact 20 ms frames (320 samples / 640 bytes).
3. Native and delivered formats, channel policy, conversion implementation and
   capability result are observable in config, logs and tests.
4. Listen, VAD and ASR receive the delivered format and perform no additional
   implicit resampling or sample-format conversion.
5. Stop, failure and reopen reset ALSA, conversion and partial-frame state and
   leave no stream, task or device owner.

## 4. Required configuration correction

The current single `AudioConfig` cannot represent both native and delivered
formats, and `bit_depth: Literal[16]` cannot describe the S32_LE device. Core
Team should separate input and output configuration and distinguish at least:

- device/backend and device identifier;
- native device sample rate, channels and sample format;
- delivered stream sample rate, channels, sample format and frame duration;
- channel selection/downmix policy;
- pinned adaptation/resampler implementation and enabled/disabled policy.

Strict validation must reject an unsupported native format or an undeclared
format mismatch. Generic example config must not contain operator account,
endpoint, private path or other deployment-specific access data.

The current Core configuration text also needs a consistency correction:
`core_audio_m3_requirements.md` permits AudioOutput rate to differ from input,
while the available `ch10_config.md` snapshot says AudioInput and TTS output
formats must match. Input and output formats must be independently configured.

## 5. Required implementation behaviour

The real AudioInput path must explicitly perform:

```text
ALSA hw: 48 kHz stereo S32_LE
  -> select/downmix the wired mic channel
  -> interpret the valid microphone bits in the S32 container
  -> anti-alias filtering and pinned 3:1 resampling
  -> saturating S16_LE conversion
  -> exact 320-sample / 20 ms framing
  -> AudioInput.frames()
```

Naive sample dropping is not acceptable. The implementation choice, version,
license and parameters must be pinned. Core Team must measure conversion CPU,
latency, buffering and signal-quality impact on Raspberry Pi 5.

## 6. Authoritative documents and source expected to change

Core Team should update, at minimum:

- `docs/implement/ch02a_core_hal.md`: native/delivered format semantics,
  adaptation ownership, lifecycle and capability behaviour;
- `docs/implement/ch10_config.md`: separate input/output and native/delivered
  config, strict validation and cross-validation;
- `docs/specs/arch.md`: explicit Audio HAL adaptation responsibility without moving
  VAD/ASR into HAL;
- `config.example.yaml` and config loader/tests;
- `src/sbd/core/audio` real backend/factory and related config models;
- Core M3 Pi acceptance tests and deployment documentation.

Core Team may choose exact class and field names. The behavioural contract and
evidence requirements in this delivery are the cross-team acceptance boundary.

## 7. Required tests and return evidence

Core M3 return delivery must include:

1. Deterministic S32 stereo fixtures covering channel selection, silence,
   impulse/sine, clipping and invalid input.
2. Resampling quality/alias-rejection tests and exact output length tests.
3. Proof that each returned frame is 640 bytes with the required 20 ms cadence.
4. Strict config tests for native/delivered mismatch and unavailable device.
5. Start/stop/reopen/cancel/failure tests that reset conversion state and leave
   no stream, task or device owner.
6. Pi 5 latency, CPU, RSS, temperature, throttling and xrun evidence.
7. Source, tests, documents and deployment instructions at one complete
   40-character Core M3 SHA.

## 8. AudioOutput forward requirement

The target playback device is also native 48 kHz stereo S32_LE. P3 remains
pending until the POC selects a TTS winner. Core M3 should design output config
with the same native-versus-stream separation, but must not assume or silently
convert a final TTS format before P3 is delivered.

## 9. Effect on POC schedule

Core Designer accepted the Option A responsibility boundary in
`DELIVERY-AUDIO-POC-M3-ACK-002`. M1 change-request closure now requires the POC
to complete `DELIVERY-AUDIO-POC-M3-VALIDATION-001`, return an exact SHA, and
receive the Core final selection ACK. The complete Core M3 backend SHA remains
a separate blocking dependency at POC M3 entry.

POC real candidate runs remain blocked until the separate frozen-gate Tester
verification, deterministic fake, schemas and fixture catalog are complete.

## 10. Core Team response requested

Core Team should return a PM-handoff acknowledgment containing:

- accept/reject decision for Option A and any bounded amendment;
- the authoritative config/design locations changed;
- the selected conversion implementation and license plan;
- the Core M3 tracking branch/issue and eventual full delivery SHA;
- any new risk that makes final delivery unreachable.
