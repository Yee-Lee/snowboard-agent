# M3-ENTRY-LOCK-002

Status: `CORRECTED PROPOSAL / M2 CLOSURE REVIEW PENDING / M3 NOT STARTED`

This packet supersedes the VAD no-go disposition and step 6 in
`M3-ENTRY-LOCK-001`. Its Core identities, topology and other candidate locks
remain unchanged.

## Exact entry identities

- Core accepted Option A POC delivery:
  `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`.
- Core Audio HAL implementation/test SHA:
  `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`.
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

## Bounded lifecycle retest

Retain steps 1–5 from `M3-ENTRY-LOCK-001`. Replace its VAD no-go step with:

6. Run Silero on the fixed M3 mic packet under the exact profile above. Prove
   start/stop/cancel/failure/reopen cleanup, retain raw probability/boundary
   diagnostics in the controlled store, and publish only sanitized evidence.
   A provisional M2 advance is not an M3 hardware `PASS`.

M3 remains `NOT_STARTED` until Reviewer/Designer closes M2 and accepts this
entry lock.
