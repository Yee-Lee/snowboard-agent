# M3-NATIVE-DISPLAY-001 — SSD1351 Hardware Capability

狀態：`PENDING`

## Test packet

| Field | Value |
|---|---|
| Purpose | Verify the selected SSD1351 fixture, native ABI, lifecycle, failure propagation, performance evidence and cleanup. |
| Source full SHA | `PENDING` |
| Target | Raspberry Pi 5 model/revision `PENDING` |
| Module | Waveshare 1.5-inch RGB OLED / SSD1351, revision `PENDING` |
| Config SHA-256 | `PENDING` |
| `.so` SHA-256 | `PENDING` |
| Command | `bash poc_display/tools/m3_ssd1351_capability.sh <operator-config>` |
| Raw evidence custody | Protected operator bundle; location not stored in Git |

## Automated results

| Check | Result | Sanitized observation |
|---|---|---|
| Environment / exact clean SHA | `PENDING` | |
| Clean native build | `PENDING` | Compiler/lgpio versions and artifact hash recorded. |
| ABI and strict config | `PENDING` | |
| Wrong buffer length | `PENDING` | |
| Missing SPI device / startup exception | `PENDING` | |
| Repeated stop / reopen 3× | `PENDING` | |
| SPI/gpiochip owners before and after | `PENDING` | |
| Full-frame latency | `PENDING` | samples=`PENDING`, warm-up=`PENDING`, P50=`PENDING`, P95=`PENDING`, max=`PENDING` |

## Operator observations

| Check | Result | Sanitized observation |
|---|---|---|
| Fixture revision/photo hash | `PENDING` | |
| Black/white/RGB/gradient color order | `PENDING` | |
| Rotation/orientation | `PENDING` | |
| Readability/flicker | `PENDING` | |

## Decision and retained limits

- Result: `PENDING`.
- Effective SPI speed availability: `PENDING`; requested speed is not reported as measured throughput.
- Full-frame only, RGB565 MSB-first, rotation 0.
- This packet is POC fixture verification; it does not replace Core Tester M3 acceptance.
