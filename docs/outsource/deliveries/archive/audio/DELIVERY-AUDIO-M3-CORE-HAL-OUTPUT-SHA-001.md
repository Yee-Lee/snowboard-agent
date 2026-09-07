# DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-001

**Date**: 2026-08-23
**From**: Core Designer
**To**: Audio POC Team (M3)
**Subject**: AudioOutput HAL 16kHz to 48kHz Adaptation Delivery
**Status**: `OFFICIALLY DELIVERED — READY FOR M3 TEST PACKET UPDATE`
**Authority**: `CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001` / `RESP-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001`

---

## 1. Resolution and Identity

Core has completed the implementation and validation of the AudioOutput HAL adaptation. This resolves the gap where `AlsaAudioOutput.play()` previously required native 48kHz / stereo / S32_LE frames, blocking the playback of Matcha 1.13.5 (16kHz / mono / S16_LE) in the Audio POC M3 test packet.

The explicit adaptation is an M3 HAL append-only revision on the `core` branch. 

**New Authoritative Core Implementation SHA**:  
`55f3526fd0a37a8831bdff769ea3ba61e5cd0684`

The POC Option A validation identity (`de3b0bab4daaf47f62956d4b27f6697b3d4fa823`) and the superseded M3 acceptance commit (`2fb2e18f934c3d06392074adba3c4518402101e9`) remain as historical references and must not be altered.

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

1. Update the M3 hardware test packet (e.g. `M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001`) to use the new Core SHA `55f3526fd0a37a8831bdff769ea3ba61e5cd0684` for all capture and playback operations.
2. Complete local runner validation without any POC-side resampling layers.
3. Submit the finalized test packet for Core Designer sign-off before proceeding to formal physical Pi execution (P1–P8).

The M4A-P9 dependency remains parallel and is unblocked by the separate `DELIVERY-P9-SURROGATE-SPEC-001`.
