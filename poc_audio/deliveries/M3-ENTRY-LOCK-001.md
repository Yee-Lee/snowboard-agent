# M3-ENTRY-LOCK-001

Status: `PROPOSED / NOT STARTED`

## Exact entry identities

- Core accepted Option A POC delivery:
  `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`.
- Core Audio HAL implementation/test SHA:
  `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`.
- Target topology: Raspberry Pi 5 + INMP441 input + MAX98357A output using the
  accepted VoiceHAT overlay and explicit 48 kHz-to-16 kHz Option A conversion.
- ASR: base Q8 primary, small Q8 fallback, P0 + greedy + fixed domain prompt.
- TTS: Matcha 1.13.5 M3 finalist; legal limitation remains outside internal
  technical validation and blocks final adoption/redistribution.
- VAD: M2 evidence-backed no-go recommendation; no VAD engine is silently
  substituted in M3.

The two Core SHAs are taken from
[`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../../docs/pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md).
M3 entry requires the receiving product checkout to prove the implementation
SHA is available and clean; this document does not modify or accept that repo.

## Bounded M3 lifecycle retest packet

After M2 closure and before any qualification claim:

1. Record clean POC and Core HAL full SHAs, Pi/platform/kernel, topology,
   capture/playback devices, PCM formats, temperature, throttle and device owner.
2. Run one AudioInput start/READY/read/stop path and one reopen path; verify
   exact 20 ms / 320-sample 16 kHz mono S16_LE output after the accepted HAL
   conversion.
3. Run one cancellation and one injected input failure; require bounded terminal
   result and zero stream/task/thread/device-owner residue.
4. Run one AudioOutput start/write-complete/stop path with Matcha native 16 kHz
   PCM, then one cancellation/failure path; require ordered complete consumption
   or explicit bounded error and zero residue.
5. Run ASR primary on the fixed M3 mic packet; activate small Q8 only under a
   separately recorded primary hard-failure/finalist rule. Preserve raw output
   in the controlled store and publish only sanitized evidence.
6. Record the M2 VAD no-go in the M3 decision table. Do not add a replacement
   VAD, tune an M2 row, or reinterpret the no-go as a hardware PASS.

This is the minimum high-risk retest packet. It does not authorize M3 before M2
is formally complete and does not replace the full M3 exit gate or M4 combined
validation.
