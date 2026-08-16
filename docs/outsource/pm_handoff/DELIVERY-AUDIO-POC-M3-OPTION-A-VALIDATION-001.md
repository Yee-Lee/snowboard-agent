# DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001

- **Parent requirement:** `DELIVERY-AUDIO-POC-M3-VALIDATION-001`
- **Response to receipt:** `DELIVERY-AUDIO-POC-M3-P4-ACK-003`
- **POC implementation/test SHA:** `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`
- **Disposition:** `POC RETURN SUBMITTED — CORE FINAL SELECTION ACK REQUESTED`

## Complete return packet

The machine-readable [manifest](../evidence/m3_option_a/manifest.json) binds
P4-A01 through A10 status, source/config/runner hashes, candidate provenance,
sanitized environment, commands, timestamps, and controlled raw-retention
paths. [results.json](../evidence/m3_option_a/results.json) and the four
sanitized P4 summaries are the review index; raw PCM, wheels and native
binaries remain Git-ignored in the manifest-relative Pi packet directories.

## Decision table

| Item | POC recommendation and evidence-backed rationale |
| --- | --- |
| Direct ALSA binding | `pyalsaaudio==0.11.0`, sdist SHA and PSF-2.0 license in candidate provenance. It realized direct `hw:` 48 kHz/stereo/S32_LE and links `libasound.so.2`. Reject `plughw:` because it hides conversion; do not select this as production dependency until Core ACK. |
| Resampler | `samplerate==0.2.4`, MIT, source SHA in provenance; `sinc_best`, state retained across chunks, explicit flush with 429 zero drain inputs. Reject per-chunk reconstruction/sample dropping. |
| Valid-bit mapping | Wiring selects channel 0. Decode signed 24-bit left-aligned S32_LE as `float32(s32 >> 8) / 8388608`, then saturate to S16. See P4-A02 and manifest raw path. |
| Buffering | Direct blocking `RW_INTERLEAVED`; period 960 frames, 4 periods / 3840-frame buffer. Five-minute shared-clock run had zero xruns; capture-to-yield p95 20.009 ms. |
| Async I/O | Two bounded blocking workers own capture/playback; asyncio heartbeat stays on the event loop. Ten reopen/cancel/failure paths ended with zero task/thread/fd/ALSA-owner counters. |
| Deployment | Pi 5 Debian 13/aarch64; Python 3.13.5, CMake 3.31.6, GCC/G++ 14.2.0, ALSA 1.2.14. Use `run_option_a_a10_clean_build.sh` with verified sources/build wheels and package index disabled; retain PSF-2.0, MIT, BSD-3-Clause and BSD-2-Clause notices. |
| Residual risk | Generated wheels/native binaries are evidence, not Core references; pyalsaaudio legacy build path emits deprecation warning. P1 native 16 kHz/mono/S16_LE remains unavailable, so conversion must remain explicit. Core must select/freeze the production binding, valid-bit allowlist, buffering and async model. |

## Gate boundary

All P4 technical results are `PASS`; this document is not a Core final
selection ACK and does not unblock the M3 Audio real backend. Core Tester must
still validate the resulting Core exact implementation SHA.
