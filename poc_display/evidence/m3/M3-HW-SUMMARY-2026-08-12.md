# M3-NATIVE-DISPLAY-001 — SSD1351 Hardware Capability

狀態：`PASS`

## Test packet

| Field | Value |
|---|---|
| Source full SHA | `5c2b6ba532a2661d5db79e27736e79890931515f` |
| Target | Raspberry Pi 5 Model B Rev 1.1 / aarch64 / Debian 13 / kernel `6.12.47+rpt-rpi-2712` |
| Module | Waveshare 1.5-inch RGB OLED / SSD1351, revision `operator-verified` |
| Fixture | co-I2S: DC=BCM24/Board18; RST=BCM25/Board22; CE0=BCM8/Board24 (SPI kernel-managed) |
| Config SHA-256 | `973229d06ae7c2734e96ce350365e61d64e2074b47166497a09976e38246d679` |
| `.so` SHA-256 | `2dd44a17abd57a195674ddcf12717bbb2759580e81bbf194723507232ad50493` |
| Compiler / lgpio | Debian GCC 14.2.0 / lgpio `0.2.2-1~rpt1+trixie` |
| Raw evidence custody | Pi `poc_display/evidence/m3/20260812T145653Z-ssd1351/`; tar-stream SHA-256 `affcfd5f58c9c97b348737a78cd4f2a81c7595a75fbeb6ba2e5188a7a38bd558` |

## Automated results

| Check | Result | Sanitized observation |
|---|---|---|
| Exact clean SHA / environment | `PASS` | Pi SHA matches source; clean worktree; SPI enabled; no throttling. |
| Pi clean build / runtime relocation | `PASS` | `make` and `ldd -r libdisplay.so` passed; no undefined symbol. |
| Strict config and ABI | `PASS` | SPI0 CE0, gpiochip0, RGB565 MSB-first, 128×128 full frame. |
| Wrong buffer length | `PASS` | Rejected. |
| Missing SPI device | `PASS` | Rejected. |
| Repeated stop / reopen | `PASS` | Reopen `3/3`; idempotent stop passed. |
| Frame intent | `PASS` | Black, white, red, green, blue and gradient frames presented. |
| Full-frame latency | `PASS` | 10 warm-ups; 100 samples; P50 `65.8713625 ms`, P95 `65.879723 ms`, max `65.897834 ms`. |
| Cleanup | `PASS` | No SPI/gpiochip owner remained after diagnostics. |

## Operator observations

| Check | Result | Sanitized observation |
|---|---|---|
| Fixture/wiring and revision | `PASS` | Owner-confirmed co-I2S fixture and revision; photos not required. |
| Black/white/RGB/gradient color order | `PASS` | Owner visually confirmed on the physical OLED. |
| Rotation/orientation | `PASS` | Owner-confirmed. |
| Flicker | `PASS` | Owner-confirmed. |

## Decision and retained limits

- Result: `PASS` for this POC hardware capability packet.
- Requested SPI speed: `4,000,000 Hz`; effective speed was unavailable and is not inferred from latency.
- Measurement boundary: immediately before adapter `show()` to native `present` return.
- Full-frame only, RGB565 MSB-first, rotation 0.
- This POC fixture verification does not replace Core Team M3 integration acceptance.
