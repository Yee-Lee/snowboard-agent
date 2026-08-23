# M3-ENTRY-LOCK-002

Status: `CORE OUTPUT ADAPTATION DELIVERED / PACKET SIGN-OFF PENDING / M3 NOT STARTED`

This packet supersedes the VAD no-go disposition and step 6 in
`M3-ENTRY-LOCK-001`. Its Core identities, topology and other candidate locks
remain unchanged.

## Exact entry identities

- Core accepted Option A POC delivery:
  `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`.
- Audio POC Option A implementation/test validation SHA:
  `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`.
- Existing Core M3 accepted Audio HAL implementation SHA:
  `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`; acceptance commit/tag
  `2fb2e18f934c3d06392074adba3c4518402101e9` / `core_m3`.
- M3 formal execution Core HAL SHA:
  `ff09199583644a8f0822153e371589f52ae821a0`, delivered by
  `DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-002`; it includes the accepted 16 kHz
  mono S16_LE stream to 48 kHz stereo S32_LE native output adaptation.
- Target topology: Raspberry Pi 5 + INMP441 input + MAX98357A output using the
  accepted VoiceHAT overlay and explicit 48 kHz-to-16 kHz Option A conversion.
- ASR: base Q8 primary, small Q8 fallback, P0 + greedy + fixed domain prompt.
- TTS: Matcha 1.13.5 M3 finalist; legal limitation blocks final adoption and
  redistribution but not internal technical validation.
- VAD: Silero 6.2.1 provisional finalist at exact POC implementation SHA
  `5188e3af360ba3b63f5eedb16288d39bc849cacc`; model SHA-256
  `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.

## VAD M3 qualification lock

Start with the M2 profile unchanged: 16 kHz input, official 64-sample context,
threshold `0.5`, negative threshold `0.35`, minimum speech 250 ms, startup mask
160 ms, silence close 500 ms, and 500/600 ms capture padding.

M3 must qualify low-volume leading-syllable retention on the pinned target mic
and HAL. Do not silently lower model thresholds. If real target capture shows a
material level problem, propose one fixed front-end gain with clipping,
silence, impact-noise, ASR and cleanup regression checks before applying it.
No gain, threshold or padding matrix is authorized by this entry lock.

The M3 mic packet must include normal speech, low-volume starts, natural pause,
silence, object impacts, cough and playback-speech observations. Playback source
rejection/AEC remains outside the basic VAD and current POC scope.

## Core output adaptation disposition

Core SHA `ff09199583644a8f0822153e371589f52ae821a0` closes the output-format gap
inside `AudioOutput`; Matcha remains a native 16 kHz mono producer and POC must not
insert a TTS/Speak resampler. This blocker is closed. Formal M3 execution remains
stopped only until the committed POC packet receives Core Designer sign-off.

## Bounded lifecycle retest

Retain steps 1–5 from `M3-ENTRY-LOCK-001`. Replace its VAD no-go step with:

6. Run Silero on the fixed M3 mic packet under the exact profile above. Prove
   start/stop/cancel/failure/reopen cleanup, retain raw probability/boundary
   diagnostics in the controlled store, and publish only sanitized evidence.
   A provisional M2 advance is not an M3 hardware `PASS`.

Reviewer/Designer 已關閉 M2 並接受本 entry lock。M3 formal hardware execution
仍維持 `NOT_STARTED`，直到 locally verified packet/runner 取得 exact candidate SHA
與 Core Designer packet sign-off。
