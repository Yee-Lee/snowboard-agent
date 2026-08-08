# CR-AUDIO-M3-PCM-001 — Explicit AudioInput Format Adaptation

狀態：`PROPOSED / AWAITING DESIGNER DECISION`
日期：2026-08-08
提出方：Audio POC Tester
決策方：User/Designer and Core Team Designer

## Trigger

`M1-NATIVE-AUDIO-001` proves that the target INMP441 + MAX98357A configuration
exposes only 48 kHz, stereo, S32_LE through direct ALSA `hw:` capture and
playback. The accepted AudioInput contract requires 16 kHz, mono, S16_LE,
20 ms frames. `plughw:` can convert this silently, but hidden conversion is not
acceptable delivery evidence.

## Impact

- Core M3 cannot claim that the current hardware natively meets AudioInput
  config defaults.
- POC M3 cannot integrate the current contract without a named, tested format
  adaptation boundary.
- VAD/ASR candidates still need a stable 16 kHz mono input contract; changing
  them individually would make comparison and product integration inconsistent.

## Options

### A — Explicit adaptation inside Core AudioInput HAL (recommended)

Open the real device at 48 kHz, stereo, S32_LE. Inside the real AudioInput
backend, explicitly select/downmix the mic channel, convert bit depth,
resample to 16 kHz, and produce exact 20 ms mono S16_LE frames. Configuration,
logs, capability results, tests, and documentation must distinguish native
device format from delivered HAL format. Listen/VAD/ASR must not add another
implicit conversion.

Cost/risk: Core M3 must choose and pin a conversion implementation, measure CPU,
latency and signal quality on Pi 5, and prove cancel/reopen/cleanup paths.

### B — Change the product contract to native 48 kHz stereo S32_LE

Expose the hardware-native format to Listen and make downstream VAD/ASR
adapters perform explicit conversion.

Cost/risk: higher bandwidth and memory, duplicated candidate adaptation,
greater comparison variance, and a broader product-contract change. Not
recommended for the current POC.

### C — Change driver/overlay or target hardware

Find a supported configuration that exposes exact 16 kHz mono S16_LE natively,
or replace the target audio hardware.

Cost/risk: new hardware/driver bring-up and schedule uncertainty; the current
working shared-clock topology would require requalification.

## Recommendation and interim rule

Approve Option A. Core Team may continue M3 API/config and native backend work,
but must not mark AudioInput accepted until the explicit conversion is pinned
and cross-validated. Audio POC may continue M1 fake/harness/fixture work, but
must not start real VAD/ASR/TTS candidate runs until the frozen-gate Tester
verification is complete.

## Decision record

| Decision | Owner | Status |
| --- | --- | --- |
| Select A, B, C, or reject all | User / Designer | `PENDING` |
| Accept matching Core M3 change | Core Team Designer | `PENDING` |
| Update contract delivery and cross-validation tests | Audio POC / Core Team | `PENDING` |
