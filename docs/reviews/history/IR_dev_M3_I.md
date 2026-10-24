---
requestor: "Developer"
owner: "Designer"
status: "Resolved"
---

# IR_dev_M3_I — SSD1351 native GPIO chip config boundary

## Blocking finding M3-DISPLAY-CONFIG-001

- Contract basis: Ch 10 §7 defines the complete `DisplayConfig` real-only field set and requires `make_display(config)` to receive that validated object unchanged. Developer may not alter the approved public factory API. Ch 2a requires validation before GPIO/SPI claim.
- Accepted input: Display POC source `5c2b6ba532a2661d5db79e27736e79890931515f`, `src/sbd/core/display/native/include/pin_config.h` / `hal/ctypes_backend.py`, ABI v1 `_CDisplayConfig.gpio_chip.chip_index`.
- Evidence: the accepted adapter rejects a negative/unresolved chip index before `display_open()`. Its target config requires an operator-resolved integer `gpio.chip`. Core Ch 10 `DisplayConfig` has no gpiochip field; `GPIOConfig.chip` is a separate string and is not passed to `make_display(config)`.
- Expected: Core can provide an operator-validated gpiochip identity to ABI v1 without hidden global reads, hardcoded target assumptions, or a second config parser.
- Actual: the adapter cannot construct the required ABI struct from its approved input. Hardcoding index `0` would make config/evidence inaccurate and could claim the wrong GPIO controller.
- Impact: WP-M3-10 native adapter start, DSPI target tests, and integrated Display acceptance are Blocked. Renderer, Arbiter, strict artifact/SPI/DC/RST validation, and Null/Mock paths remain implementable.
- Suggested resolution: Designer should either add an explicit validated gpiochip index/path field to `DisplayConfig`, or define an approved composition/factory injection that preserves one authoritative strict loader. Update Ch 10, config example, M3 test spec trace if needed, and the factory signature only if explicitly approved.
- Minimum acceptance: one documented, path-aware config value reaches ABI v1 `gpio_chip.chip_index`; invalid/unresolved values fail before `ctypes.CDLL`/GPIO/SPI; mock/null cannot carry it; no hardcoded index or environment/global probe.

## Developer disposition

WP-M3-10 remains Blocked pending Designer revision. No POC source, binary, wheel, or `.so` is copied into Core Git. The exact reference checkout remains outside Core at `/tmp/snowboard-display-reference-5c2b6ba532a2661d5db79e27736e79890931515f`.

## Designer response — 2026-08-13

- Disposition: **Revised**.
- Ch 10 §7 adds SSD1351-only `DisplayConfig.gpio_chip_index: int | None`. The strict loader requires an integer in ABI v1's signed-int32 range `0..2147483647` for `driver="ssd1351"`; mock/null carrying it is rejected.
- The adapter mapping is normative: the validated value is written unchanged to ABI v1 `_CDisplayConfig.gpio_chip.chip_index`. Reading `GPIOConfig.chip`, environment/global state, probing a default controller, or hardcoding index `0` is forbidden.
- `make_display(config)` remains unchanged and receives the single validated `DisplayConfig`; no second parser or composition input is introduced.
- `config.example.yaml` keeps the field `null`. The existing `M3-CFG-001` missing-real-field / GPIO / mock-null criteria already cover this risk; the M3 milestone and concrete regression cases now name the gpiochip boundary without changing Tester-owned acceptance scope.
- Developer regression coverage is added to `tests/test_m3_cfg_001_002.py`. WP-M3-10 may resume after the focused verification below passes.

## Developer re-review — 2026-08-13

- Disposition: **Resolved**. `DisplayConfig.gpio_chip_index` is now an explicit, validated input that can be mapped directly to ABI v1 without changing `make_display(config)`.
- Focused verification: `23 passed` for M3 config plus config/HAL regression tests.
- Full non-RPi verification: `233 passed, 1 deselected`.
- Missing, negative, and signed-int32 overflow indexes fail with a `core.display.gpio_chip_index` error before factory/native access; mock/null reject the real-only value. The Developer accepts the equivalent resolution and unblocks WP-M3-10.
