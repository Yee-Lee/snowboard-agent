# Core Team → POC Audio Team: M3 Option A Conditional Acceptance

- **Delivery ID**: `DELIVERY-AUDIO-POC-M3-ACK-002`
- **References**: `CR-AUDIO-M3-PCM-001`、`DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001`、`M1-NATIVE-AUDIO-001`
- **POC evidence source SHA**: `0edeb7d9f8ff3811d1480ab4b464db2842978233`
- **POC delivery SHA**: `87ff000559ded8c0d7499d621af7dfcccb81858c`
- **Status**: `OPTION A DIRECTION ACCEPTED — IMPLEMENTATION VALIDATION REQUIRED`
- **Date**: 2026-08-13
- **Architecture change**: `No`

## 1. Decision

Core Designer接受`CR-AUDIO-M3-PCM-001`的Option A產品方向：real `AudioInput`在HAL內顯式將direct ALSA native format轉成既有delivered stream contract。POC P1維持`FAIL`，不得把target hardware改寫成native支援16 kHz / mono / S16_LE，也不得以`plughw:`隱藏轉換；P2 device / config / wiring evidence為`PASS`。

本決定只固定責任邊界與可觀察結果，不核准尚未在目標Pi驗證的ALSA binding、valid-bit alignment、resampler、buffer / period參數或async I/O模式。這些項目由`DELIVERY-AUDIO-POC-M3-VALIDATION-001`發包驗證。

本修正仍位於`core/audio` library adapter內，不新增process、IPC、public HAL方法或跨模組ownership，也不把VAD / ASR / TTS搬進HAL，因此不需Architecture change或`AR_impl`。

## 2. Accepted contract

```text
direct ALSA hw: 48 kHz / stereo / S32_LE
  -> select configured INMP441 L/R channel
  -> decode evidence-confirmed valid microphone bits
  -> stateful streaming anti-alias 3:1 conversion
  -> round + saturate to S16_LE
  -> exact 320-sample / 640-byte / 20 ms frames
  -> AudioInput.frames()
```

Native與stream format、device、channel、valid-bit semantics、resampler及buffering都必須進入strict config與sanitized startup evidence。Listen / VAD / ASR不得再轉換。`aclose`、cancel、failure、stop與reopen必須釋放ALSA owner並重置conversion與partial-frame state。

## 3. Package gate

| Package | Developer status before POC return |
| :--- | :--- |
| Audio Protocol、mock/null、native / stream config schema、fake-source seam / test skeleton | `READY` |
| Display、Camera、GPIO與其他M3工作包 | `READY` |
| Audio direct ALSA real backend | `BLOCKED BY AUDIO P4` |
| Production binding / resampler dependency lock | `BLOCKED BY AUDIO P4` |
| Valid-bit allowlist、buffer / period、async I/O final implementation | `BLOCKED BY AUDIO P4` |
| M3 Audio real acceptance | `BLOCKED BY AUDIO P4 + CORE EXACT-SHA TEST` |

候選`pyalsaaudio==0.11.0`與`samplerate==0.2.4`僅是POC起始探索組合，不是Core selected baseline。Developer不得引用候選名稱解除Blocked、加入production lock或開始real backend。

## 4. Output boundary

POC P3 TTS winner仍為`PENDING M4a`，不阻擋本次AudioInput validation。M3 AudioOutput fixture直接匹配48 kHz / stereo / S32_LE native output；P3完成前不得加入output runtime adaptation。TTS / Speak未來須匹配`audio.output.stream_format`，不得在worker內隱式轉換。

## 5. Required response

Audio POC依`DELIVERY-AUDIO-POC-M3-VALIDATION-001`回交一個完整40-character source SHA。Core Designer審核required evidence後將另發final selection ACK，明列核准binding、resampler、版本 / hash / license、valid-bit alignment、buffering與async I/O模式；只有該final selection ACK可以解除Audio P4。

POC自驗只解除implementation selection gate，不能取代Core Tester對M3 exact implementation SHA的獨立驗收。
