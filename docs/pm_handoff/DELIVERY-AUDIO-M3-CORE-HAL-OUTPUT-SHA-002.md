# DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-002

**Date**: 2026-08-23
**From**: Core Designer
**To**: Audio POC Team (M3)
**Subject**: AudioOutput HAL 16kHz to 48kHz Adaptation Delivery (Fix)
**Status**: `OFFICIALLY DELIVERED — READY FOR M3 TEST PACKET UPDATE`
**Authority**: `CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001` / `RESP-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001`

---

## 1. Resolution and Identity

Core has amended the implementation and validation of the AudioOutput HAL adaptation. This delivery supersedes `DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-001` which contained contradictions in documentation state and test coverage gaps.

The explicit adaptation is an M3 HAL append-only revision on the `core` branch. 

**New Authoritative Core Implementation SHA**:  
`ff09199583644a8f0822153e371589f52ae821a0`

The previous SHA (`55f3526fd0a37a8831bdff769ea3ba61e5cd0684`) is deprecated and must not be used in the test packet.

---

## 2. Implemented Contract

- **`StreamFormatAdapter`** handles stateful conversion inside `AlsaAudioOutput`.
- Audio POC's TTS module (Matcha) acts as a strict `16,000 Hz / mono / S16_LE` producer.
- `AudioOutput.play()` accepts ordered `S16_LE` chunks of any legal size.
- Resampling (`samplerate.sinc_best`), channel duplication (mono → stereo), and scaling (S16_LE → S32_LE) are executed entirely by Core before writing to the ALSA backend.
- The lifecycle cleanly flushes the resampler tail and discards state upon EOF or cancellation.

---

## 3. Next Steps for Audio POC

With this implementation delivered, Audio POC is authorized to:

1. Update the M3 hardware test packet (e.g. `M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001`) to use the new Core SHA `ff09199583644a8f0822153e371589f52ae821a0` for all capture and playback operations.
2. Complete local runner validation without any POC-side resampling layers.
3. Submit the finalized test packet for Core Designer sign-off before proceeding to formal physical Pi execution (P1–P8).
