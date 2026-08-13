# Audio POC → Core M3 Audio HAL Contract v1.0

Delivery ID：`DELIVERY-AUDIO-POC-M3-CONTRACT-001`
狀態：`ACCEPTED WITH CONDITIONS`
版本：`1.0`
日期：2026-08-08
提供方：Audio POC / User as Designer
接收方：Core Team Designer

## 1. Authority and acceptance

This delivery supersedes the v0.1 draft as the POC-to-Core M3 design input.
Core Team accepted the contract with the conditions in
`docs/pm_handoff/history/DELIVERY-AUDIO-POC-M3-ACK-001.md`. The acknowledged Core
development branch is `dev_agent_m3`; its final integration SHA is not yet
available and must not be inferred from the branch name.

This document lets Core Team start M3 design and implementation. It is not a
POC M3 integration baseline. POC M3 starts only after Core Team supplies an
accepted full 40-character SHA and the POC has M2 finalists.

## 2. Accepted contract

| Area | Contract |
| --- | --- |
| Target hardware | Raspberry Pi 5; INMP441 mic and MAX98357A speaker amplifier sharing I2S BCLK/LRCK; `googlevoicehat-soundcard` overlay. |
| Input API | `start()`, `stop()`, and `frames() -> AsyncIterator[bytes]`; one active iterator per instance. |
| Output API | `start()`, `stop()`, and `play(pcm: AsyncIterator[bytes])`; consume every legal PCM chunk. |
| Input PCM target | 16 kHz, mono, 16-bit little-endian, 20 ms frame; format is fixed in config. |
| Output PCM | Configurable independently from input; final rate/shape follows the POC TTS winner. Speak must not implicitly resample. |
| Lifecycle and errors | Input/output independently start, stop, and reopen. Stop leaves no stream, task, or device owner. Invalid device exposes error/fallback/capability. |
| Boundaries | HAL owns PCM I/O, device lifecycle, capability, and error only. VAD, endpointing, ASR, TTS candidate logic, AEC, barge-in, wake word, and cross-process mic handoff are excluded. |

## 3. Conditions and POC dependencies

| ID | Required POC delivery | Status | Consequence if unresolved |
| --- | --- | --- | --- |
| P1 | Native `hw:` PCM matrix for rate/channel/sample format, 16 kHz feasibility, xrun behaviour, and lifecycle evidence. | `FAIL / OPTION A DIRECTION ACCEPTED` | Native device is fixed at 48 kHz, stereo, S32_LE; P4 implementation validation and Core final selection ACK remain required. |
| P2 | ALSA card/device identifier, driver config hash, wiring and power confirmation, supplied through local config/evidence rather than generic source. | `PASS` | Closed by `M1-NATIVE-AUDIO-001` and `M1-HW-SMOKE-001`. |
| P3 | TTS winner PCM rate/channels/bit depth/chunk behaviour and controlled fixture. | `PENDING M2` | POC M3 playback-winner evidence is blocked; Core Output API remains configurable. |

## 4. Core Team return delivery required for POC M3

Core Team must provide an accepted full 40-character SHA containing source,
tests, and authoritative documentation, plus Pi setup/configuration, automated
input/output/lifecycle/fallback/cleanup evidence, and known buffering,
sample-rate, shared-clock, xrun, and ownership limits. The POC Tester will
test only that exact SHA.

## 5. Acceptance record

| Decision | Owner | Status |
| --- | --- | --- |
| Core accepted v1.0 as M3 design input | Core Team Designer | `ACCEPTED WITH CONDITIONS` |
| POC publishes P1 native capability matrix | Audio POC Tester | `FAIL / CHANGE REQUESTED` |
| POC publishes P2 device/config evidence | Audio POC Tester / User | `PASS` |
| Core accepts `CR-AUDIO-M3-PCM-001` | Core Team Designer | `OPTION A DIRECTION ACCEPTED / P4 REQUIRED` |
| Core supplies accepted M3 SHA | Core Team Designer | `PENDING` |
| POC accepts SHA for POC M3 integration | Audio POC Tester / User | `PENDING` |
