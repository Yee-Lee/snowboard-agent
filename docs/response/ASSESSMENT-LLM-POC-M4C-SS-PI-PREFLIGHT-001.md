# ASSESSMENT-LLM-POC-M4C-SS-PI-PREFLIGHT-001

- Date: 2026-09-19
- Scope: User-authorized M4C-SS Pi preflight only
- Status: `ACOUSTIC PREFLIGHT PASS / FORMAL IDENTITY PENDING / NO EXPERIMENT EXECUTION`

## Sanitized observations

The target reported Raspberry Pi 5 Model B Rev 1.1, Debian 13, aarch64 and CPython 3.13.5. The selected
`gemma-4-E2B-it.litertlm` artifact was present with 2,588,147,712 bytes and SHA-256
`181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`, matching the frozen profile.
At observation time `get_throttled=0x0`, temperature was 34.750 C, MemAvailable was 3,865,776 KiB and
configured swap had zero bytes in use. These are engineering preflight observations, not a formal frozen-run
receipt.

ALSA inventory identified the product I2S VoiceHAT playback device separately from an `AB13X USB Audio`
capture device. The executed duplex path was explicitly:

- playback: I2S VoiceHAT speaker, stable ALSA selector `hw:CARD=sndrpigooglevoi,DEV=0`;
- capture: external USB microphone, stable ALSA selector `hw:CARD=Audio,DEV=0`;
- no I2S microphone capture, Listen, ASR or barge-in path was used.

A fixed 1 kHz, approximately 250 ms pulse was played as 48 kHz stereo S32_LE through the I2S speaker while
the USB microphone captured simultaneously. Capture succeeded and contained the pulse above ambient noise.
Although 16 kHz had been requested initially, the USB hardware negotiated 48 kHz mono S16_LE; the future
measurement profile must therefore freeze the observed 48 kHz capture rate or explicitly validate a reviewed
conversion path rather than claim native 16 kHz capture.

The temporary pulse and capture were confined to `/tmp` and removed by the completed command. No raw audio,
host name, endpoint, credential, physical artifact path, prompt or model output is retained in Git.

## Timing calibration completion — 2026-09-20

The replacement calibration harness uses only the system `arecord`/`aplay` executables and Python standard
library. It retains no PCM and timestamps each 480-frame USB capture block with the same monotonic clock used by
the controller. The workstation synthetic suite first proved both the passing bound and a 55 ms jitter case that
must remain `INCONCLUSIVE`; the module was then streamed to the Pi without creating a target file.

The repeated I2S-speaker plus USB-microphone pulse produced these sanitized engineering observations:

| Field | Observation |
| --- | ---: |
| Capture format | 48 kHz / mono / S16_LE |
| Capture period | 480 frames / 10 ms |
| Ambient baseline RMS | 181.614 |
| Frozen threshold RMS | 908.070 |
| Detected onset RMS | 2,013.916 |
| Maximum capture-clock residual | 60,403 ns |
| Detector error bound | 10,000,000 ns |
| Combined uncertainty | 20,060,403 ns |
| Required maximum | 50,000,000 ns |
| Capture/playback owners stopped | yes / yes |

The acoustic clock/detector preflight therefore passes the `<=50 ms` gate. This was still an engineering run of
workstation-streamed bytes, not formal evidence from a clean pushed execution SHA; the exact frozen command must
be repeated after execution freeze.

## Remaining fail-closed boundary

The initial `alsaaudio`-based attempt could not start because the system Python lacked that optional module; no
installation or alternate runtime search occurred. The dependency-free replacement above closes that harness
gap without changing the selected microphone or playback path.

The User also stopped further checkout/Audio-runtime inspection. Runtime wheel, native library, TTS/voice,
Audio manifest, clean checkout, private evidence root and offline-network identity were not revalidated in this
scope. No controller, mapping, live A/B, negative, LLM inference, TTS or benchmark case ran.

## Next authorized boundary

Formal M4C-SS execution still requires a clean exact pushed SHA, frozen surface/receipt, remaining runtime/TTS/
Audio identity, offline transition and separate User authorization. This assessment makes no candidate
recommendation and publishes no benchmark result.
