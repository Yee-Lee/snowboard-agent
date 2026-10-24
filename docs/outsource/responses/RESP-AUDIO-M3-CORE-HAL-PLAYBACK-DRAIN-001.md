# RESP-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001

- **Date**: 2026-08-24
- **From**: Core Designer
- **To**: Audio POC Team
- **Status**: `ACCEPTED — CORE HAL PLAYBACK DRAIN AUTHORIZED`
- **Subject**: One-time ACK for AudioOutput HAL Playback Drain Patch
- **Reference**: `CR-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001`

---

## 1. Acceptance of Replacement Core HAL Implementation

Core has reviewed and accepted candidate `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` as the authoritative append-only Core HAL replacement on the `core` branch.

| Item | Identity |
|---|---|
| Core base | `51fe185d143595702caec03eeec7b63a63e2391d` |
| Authoritative replacement SHA | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Fast-forward status | Completed on Core `core` branch |
| Superseded execution baseline | `ff09199583644a8f0822153e371589f52ae821a0` |

---

## 2. Confirmation of Accepted Semantics

Core confirms the five required playback completion and lifecycle semantics:

1. **Successful `play()`**: Fully exhausted iterator, flushed adapter tail, successful native writes, and complete ALSA `drain()` through the physical device before returning.
2. **Error and cancellation paths**: Iterator error, write error, force-abort, and cancellation skip drain and retain prompt close/drop behavior in `stop()`.
3. **Explicit failure on missing/failed drain**: Missing drain capability or drain runtime exception constitutes an explicit playback failure, never silent success.
4. **Adapter state reset**: Adapter resets after every success or failure; repeated `play()` calls on a single started device remain supported.
5. **Contract invariance**: Formats, sample scaling, resampler (`sinc_best`), period/buffer (`960 × 4`), dependency identities, and public HAL protocols remain unchanged.

---

## 3. Evidence Sufficiency

The supplied portable and target Pi verification is confirmed sufficient:
- Workstation focused suite (8 passed) and full non-RPi suite (268 passed, 21 deselected).
- Pi focused suite (8 passed) and full non-RPi suite (267 passed, 1 optional skipped, 21 deselected).
- Target Pi 5 physical speaker validation: five silent play/drain reuse cycles complete (`0.580 s`) and 6.055 s adapted speech audible and comparable in level to `aplay` control with zero device leak.

No additional tests are required.

---

## 4. Authorization for Packet Update

Audio POC is authorized to:
1. Mechanically replace superseded Core SHA `ff09199583644a8f0822153e371589f52ae821a0` with new authoritative SHA `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` in the M3 qualification packet.
2. Prepare one append-only packet and sign-off request update.

---

## 5. Named Core Owner for Final ACK

- **Named Owner**: **Core Designer**
- Following Audio's mechanical packet update, Core Designer will issue the final exact-identity ACK upon receiving the updated packet and sign-off request.
