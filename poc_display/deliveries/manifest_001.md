# Delivery Manifest: POC-DSP-001 (Draft v0.3)

Status：`P3_CAPABILITY_PASS / Core re-review pending / not Accepted`

## Source identity

| Field | Value |
|---|---|
| Repository | `snowboard-agent` |
| Branch | `dev_display_p1` |
| Comparison base | `412172ae58c8053bd697caebe133a718206c2f55` |
| Candidate source SHA | `5c2b6ba532a2661d5db79e27736e79890931515f` |
| Included scope | contract、public C header、SSD1351 native source、Python adapter、tests、config/evidence schema |

Candidate source identity 只認上述完整 SHA；後續 sanitized summary 或 review metadata commit 不得改變 Pi checkout 與 evidence 使用的 source SHA。

## Submission unit

| Field | Value |
|---|---|
| Type | Git commit；整個 tracked repository snapshot 視為單一提交包 |
| Identity | `5c2b6ba532a2661d5db79e27736e79890931515f` |
| Scope | 該 commit 可達的完整 Git tree 與 blobs |
| Normal transport | Core Team 直接取得 repository 並 checkout 完整 SHA |
| Per-file checksum | 不要求；Git commit 已識別全部 tracked content |

若改用單一 archive/bundle 傳輸，只需為整包記錄一個 SHA-256，不展開逐檔 checksum。

## External / non-uploadable materials

| Material | Status | Handling |
|---|---|---|
| Pi-built `libdisplay.so` | `PASS` | SHA-256 `2dd44a17abd57a195674ddcf12717bbb2759580e81bbf194723507232ad50493`; Pi custody |
| Actual Pi local config | `PASS` | SHA-256 `973229d06ae7c2734e96ce350365e61d64e2074b47166497a09976e38246d679`; machine-local, not uploaded |
| Raw logs/evidence | `PASS` | Pi custody `m3/20260812T145653Z-ssd1351`; tar-stream SHA-256 `affcfd5f58c9c97b348737a78cd4f2a81c7595a75fbeb6ba2e5188a7a38bd558` |

只有無法納入正常 Git 提交包的內容才使用上述例外流程。

## Target environment

| Field | Required value / status |
|---|---|
| Host | Raspberry Pi 5 Model B Rev 1.1 |
| OS / kernel | Debian GNU/Linux 13 / `6.12.47+rpt-rpi-2712` |
| Architecture | `aarch64` |
| Compiler | Debian GCC `14.2.0-19` |
| Python | `3.13.5` |
| lgpio | `0.2.2-1~rpt1+trixie` |

## Primary hardware

| Field | Value / status |
|---|---|
| Module | Waveshare 1.5-inch RGB OLED Module |
| Controller | SSD1351 |
| Module revision | `operator-verified` (photos not required) |
| Interface | 4-wire SPI0 mode 0 CE0 |
| Resolution / format | 128×128 / RGB565 MSB first / 32768 bytes |
| Pins | DC=BCM24/Board18; RST=BCM25/Board22; CS=BCM8/Board24 (SPI CE0 kernel-managed); MOSI=BCM10/Board19; SCLK=BCM11/Board23; BL absent |
| Requested speed | 4,000,000 Hz |
| Rotation | 0° pending fixture confirmation |
| Local config | copy `poc_display/config/ssd1351_pi5.example.json`, replace `revision` and `gpio.chip`, then record SHA-256 |

Optional ST7789 source is not primary SSD1351 acceptance evidence.

## Reproducible build

```bash
cd src/sbd/core/display/native/waveshare_ssd1351
make clean
make
sha256sum libdisplay.so
ldd -r libdisplay.so
```

以上命令必須由 Core Team operator／登入使用者在 exact clean candidate SHA 的 target Pi 上執行。`make` exit 0 不足以通過；`ldd -r` 若出現任何 `undefined symbol` 即為 FAIL，且 workstation/stub build 不得替代此 gate。

Target clean build、`ldd -r` and `.so` checksum: `PASS`; see `poc_display/evidence/m3/M3-HW-SUMMARY-2026-08-12.md`.

Public header standalone syntax check：

```bash
cc -std=c11 -Wall -Wextra -Werror -Isrc/sbd/core/display/native/include \
  -fsyntax-only poc_display/tests/display_header_smoke.c
```

## Verification commands

Host-safe checks：

```bash
PYTHONPATH=src python3 -m pytest \
  src/sbd/core/display/tests/integration/test_mock_smoke.py -v
```

Host verification completed on 2026-08-09:

- Python `compileall`: PASS.
- C public-header C11 syntax check with `-Wall -Wextra -Werror`: PASS.
- Mock lifecycle via stdlib `unittest`, including repeated stop: PASS.
- SSD1351 driver/runtime/vendor source compile and link against the host-only `poc_display/tests/native_stub/`: PASS.
- ctypes adapter → stub-linked native ABI start/clear/write/show/stop/repeated-stop: PASS.
- Native invalid 60 MHz config, wrong length, wrong thread and repeated close statuses: PASS via `poc_display/tests/native_abi_smoke.py`.
- Audio-derived packet runner missing-device rejection and reopen 3/3 against host lgpio stub: PASS.
- `pytest` suite: NOT RUN in that environment because neither system Python nor `.venv` contained pytest.

Host verification rerun on 2026-08-12:

- Full display `pytest` suite: PASS (`26 passed, 8 skipped`; skipped tests require the Pi/optional fixture).
- Python `compileall` and compatibility service lifecycle: PASS.
- C public-header C11 syntax check: PASS.
- SSD1351 stub-linked native build and ABI negative-path smoke: PASS.

The stub-linked `/tmp/.../libdisplay.so` is test-only and is not a deliverable artifact or hardware evidence.

Pi fixture packet（after clean immutable commit and passing pre-test）：

```bash
M3_PANEL_REVISION='<module revision>' \
M3_FIXTURE_RESULT=PASS \
M3_COLOR_RESULT=PASS \
M3_ORIENTATION_RESULT=PASS \
M3_FLICKER_RESULT=PASS \
bash poc_display/tools/m3_ssd1351_capability.sh \
  /protected/path/to/config.actual.json
```

Pi result/evidence index：`PASS`；`poc_display/evidence/m3/M3-HW-SUMMARY-2026-08-12.md`。

## Vendor provenance and license

- `OLED_1in5_rgb.c/.h` embedded header identifies Waveshare team, V2.0, 2020-08-17, with a permissive MIT-style permission notice.
- Redistribution notice and file inventory：`poc_display/NOTICE.md`。
- Candidate full Git SHA pins the delivered vendor/source files; no branch HEAD or external mutable URL is used as provenance.

## Known limits

- No 60 fps or `<20 ms` guarantee; Pi P50/P95/max are recorded in the sanitized P3 summary.
- SSD1351 baseline requested clock is 4 MHz; effective throughput remains unmeasured.
- Reference adapter supports full-frame RGB565 MSB-first and rotation 0 only.
- Native implementation supports one open handle per loaded artifact.
- Primary fixture/revision operator attestation and gpiochip0 resolution are PASS; Core design-input ACK remains pending.
- Core Tester acceptance and POC fixture verification are separate gates.
