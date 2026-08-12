# Delivery Manifest: POC-DSP-001 (Draft v0.3)

Status：`IN_PROGRESS / not immutable / not Accepted`

## Source identity

| Field | Value |
|---|---|
| Repository | `snowboard-agent` |
| Branch | `display` |
| Comparison base | `412172ae58c8053bd697caebe133a718206c2f55` |
| Delivery source SHA | `PENDING` — working tree 尚未形成包含 v0.3 的 clean 40-character commit |
| Included scope | contract、public C header、SSD1351 native source、Python adapter、tests、config/evidence schema |

Branch HEAD 或 comparison base 不代表本版 delivery source SHA。

## Artifact inventory

| Artifact | Path | SHA-256 / status |
|---|---|---|
| Contract | `poc_display/deliveries/display_m3_contract_draft.md` | `3f6b2fcb59848cdc7f415892674e1a0438bbef818b05a84d49884ec606f5b429` (working-tree snapshot) |
| Public header | `src/sbd/core/display/native/include/display.h` | `b26efcb55d992ac45885a2ac55b2d61c79bce5c18550fbe452e52419ffd5784b` (working-tree snapshot) |
| Config header | `src/sbd/core/display/native/include/pin_config.h` | `ee7c7f3f7ec7851df5fae3e2ebf8f8dbe1099738b7bec8cd351292c8303b2398` (working-tree snapshot) |
| Core Protocol | `src/sbd/core/display/base.py` | `1c8d294039e7974d23fb36e5b4c7133ba912b520c607a90c8edfbd05e9861379` (working-tree snapshot) |
| Python native adapter | `src/sbd/core/display/hal/ctypes_backend.py` | `76a5670273f9c128862f35b5616a4adf09b20046fe5d7cd12803ee4ea87d1a5f` (working-tree snapshot) |
| Adapter factory | `src/sbd/core/display/hal/factory.py` | `0ba186e5c1608db051471975807e7d08ee570799ba094508be9f3873275f385e` (working-tree snapshot) |
| Config loader | `src/sbd/core/display/hal/profiles.py` | `30a8fc4311b9492d37bee112dc29ae2634903241750f41abb7e8f085c70c4b43` (working-tree snapshot) |
| Compatibility re-export | `src/sbd/core/display/hal/protocol.py` | `a15d0bf1f0110b0d48b70017d23b3a88413c88a1878491c2e8c681527202d0f1` (working-tree snapshot) |
| SSD1351 library | `src/sbd/core/display/native/waveshare_ssd1351/libdisplay.so` | `PENDING_PI_BUILD` |
| Sanitized config example | `poc_display/config/ssd1351_pi5.example.json` | `bfe4e3edea626ea1a3fd3363a2661b5919c4b4b1df5e5fb0fb0fc696b6fe7226` |
| Pi diagnostics runner | `poc_display/tests/run_ssd1351_diagnostics.py` | `1cdd1ae8177a1a75bc5056625e25124605b6d063f705fcc051bfc5045acf6f80` |
| Remote environment pre-test | `poc_display/tools/environment_pre_test.sh` | `9a01ea21b6c63c73e8522de3aeb7c331065f52385bdd4b6a4408411d21b1c85c` |
| Pi-local M3 packet | `poc_display/tools/m3_ssd1351_capability.sh` | `302789067110aefb08e17b1e855d0c29ad716f11265e72d24ffcc6b546ad5fbe` |
| Primary run config | actual run copy under `poc_display/evidence/<delivery>/<run>/config.json` | `PENDING_PI_RUN` |

Final manifest 必須在 immutable commit 上更新 checksums；manifest 自身不列入 checksum inventory，避免 self-reference。

## Target environment

| Field | Required value / status |
|---|---|
| Host | Raspberry Pi 5; board revision `PENDING_PI_RUN` |
| OS / kernel | `PENDING_PI_RUN` |
| Architecture | expected `aarch64`; verify on target |
| Compiler | `PENDING_PI_RUN` |
| Python / pytest | `PENDING_PI_RUN` |
| lgpio | `PENDING_PI_RUN` |

## Primary hardware

| Field | Value / status |
|---|---|
| Module | Waveshare 1.5-inch RGB OLED Module |
| Controller | SSD1351 |
| Module revision | `PENDING_FIXTURE_PHOTO` |
| Interface | 4-wire SPI0 mode 0 CE0 |
| Resolution / format | 128×128 / RGB565 MSB first / 32768 bytes |
| Pins | DC=BCM25/Board22; RST=BCM27/Board13; CS=BCM8/Board24; MOSI=BCM10/Board19; SCLK=BCM11/Board23; BL absent |
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
```

Target clean build result、compiler output 與 `.so` checksum：`PENDING_PI_BUILD`。

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
M3_COLOR_RESULT=PASS \
M3_ORIENTATION_RESULT=PASS \
M3_FLICKER_RESULT=PASS \
M3_FIXTURE_PHOTO=/protected/path/to/sanitized-photo.jpg \
bash poc_display/tools/m3_ssd1351_capability.sh \
  /protected/path/to/config.actual.json
```

Pi result/evidence index：`PENDING_PI_RUN`。

## Vendor provenance and license

- `OLED_1in5_rgb.c/.h` embedded header identifies Waveshare team, V2.0, 2020-08-17, with a permissive MIT-style permission notice.
- Redistribution notice and file inventory：`poc_display/NOTICE.md`。
- The delivered vendor files are pinned by their manifest checksums; no branch HEAD or external mutable URL is used as provenance.

Vendor/source working-tree checksums:

| File | SHA-256 |
|---|---|
| `OLED_1in5_rgb.c` | `1355f1f86b2026505471f527f350db0e49fcf2caf53beda2d03c1fd31fb327a3` |
| `OLED_1in5_rgb.h` | `65c6de04419695e890c4fff56918b87cad50353bafa4825e7f92ccc886b98f64` |
| `display_driver.c` | `d7bb99e33c33de0323298d408a2489b28e14f21a2a33b546d6d32226de86253a` |
| `dev_config_runtime.c` | `dea0b099857f6e8ce10fde5aecd1e67a0a6673a304faaf1b2ddf7f43f684e7da` |
| `dev_config_runtime.h` | `d5b0c337784474a1e9f42a7f62aeb89fcae1b0a1bc00413d97659d570621668a` |

## Known limits

- No 60 fps or `<20 ms` guarantee; Pi P50/P95/max remain `IN_PROGRESS`.
- SSD1351 baseline requested clock is 4 MHz; effective throughput remains unmeasured.
- Reference adapter supports full-frame RGB565 MSB-first and rotation 0 only.
- Native implementation supports one open handle per loaded artifact.
- Primary fixture revision/photo and resolved gpiochip remain pending.
- Core Tester acceptance and POC fixture verification are separate gates.
