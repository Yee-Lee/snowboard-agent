# Core Team → POC Audio Team: M3 P4 Option A Final Selection ACK

- **Delivery ID**: `DELIVERY-AUDIO-POC-M3-P4-ACK-004`
- **Parent requirement**: `DELIVERY-AUDIO-POC-M3-VALIDATION-001`
- **Supersedes receipt disposition**: `DELIVERY-AUDIO-POC-M3-P4-ACK-003`
- **Reviewed POC delivery commit**: `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`
- **POC implementation/test SHA**: `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`
- **Decision owner**: Core Team Designer
- **Date**: 2026-08-15
- **Decision**: `ACCEPTED — M3 AUDIO REAL PACKAGE MAY START`

## 1. Decision

Core accepts the complete P4 return packet at `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`
as the selected M3 AudioInput implementation baseline. The implementation/test
SHA is an ancestor of that delivery commit. `manifest.json` and `results.json`
are valid JSON; the manifest records all ten P4 IDs as `PASS`; and all seven
tracked manifest SHA-256 entries were independently recomputed and matched.

This ACK releases the M3 Audio real-package selection gate. It does not mark
M3 accepted and does not substitute for Core Tester validation of the resulting
Core exact implementation SHA.

## 2. Selected baseline

| Area | Selected value |
| --- | --- |
| Direct binding | `pyalsaaudio==0.11.0`; sdist SHA-256 `a78a9dca33524b2c9064b34e21f5ab874272313cf324a9a77592f396a5e0fddc`; `PSF-2.0`; direct `hw:` only |
| Resampler | `samplerate==0.2.4`; sdist SHA-256 `c44dcb6fe680246f8f36588ba1f0fc7a0c5fbce710ad5e9b3812d88e8c39ac7d`; `MIT`; stateful `sinc_best`, 1:3 ratio, explicit drain |
| Capture and conversion | 48 kHz / stereo / `S32_LE`; select channel 0; signed 24-bit MSB-aligned decode: arithmetic shift right 8, scale by `8388608`, then saturate to `S16_LE` |
| Delivery | 16 kHz / mono / `S16_LE`; exactly 320 samples / 640 bytes / 20 ms per yielded frame |
| Buffering | blocking `RW_INTERLEAVED`; 960-frame period × 4 periods, 3840-frame buffer |
| Async and lifecycle | capture/playback each use a bounded blocking worker; asyncio heartbeat remains on the event loop; cancel/failure/reopen reset converter and partial-frame state and release ownership |
| Deployment | Raspberry Pi 5/aarch64, Debian 13, Python 3.13.5, ALSA 1.2.14; retain `PSF-2.0`, `MIT`, `BSD-3-Clause`, and `BSD-2-Clause` notices; use the verified clean-build flow with package indexes disabled |

`plughw:`, implicit conversion, sample dropping, and per-chunk resampler
reconstruction are not selected implementations.

## 3. Permitted work and remaining gates

- Core Developer may implement and merge WP-M3-07, its strict real-audio config,
  dependency lock, and the selected lifecycle/buffering behavior above.
- Pi-built wheels, native binaries, raw PCM, and controlled raw packets remain
  POC evidence artifacts; none are Core reference deliverables.
- Core must record a new full implementation SHA, sanitized local config hash,
  license/notice material, and reproducible test evidence.
- Core Tester must independently execute `M3-AUD-003`, `M3-AUD-004`,
  `M3-CFG-002`, and `M3-AUDI-001` through `M3-AUDI-004` against that Core SHA.
  M3 Audio and M3 overall remain unaccepted until this succeeds.

## 4. Residual risks accepted for implementation

P1 native 16 kHz / mono / `S16_LE` remains unavailable; the selected explicit
HAL conversion is therefore required. Clean target rebuilds need not produce
byte-identical generated binaries. `pyalsaaudio` retains a legacy build-path
deprecation warning; it is advisory unless it prevents the selected, verified
build flow.
