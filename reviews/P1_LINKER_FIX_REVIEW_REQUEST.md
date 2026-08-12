# P1 Native Linker Fix Review Request

狀態：`CLOSED_BY_OWNER_APPROVAL`

2026-08-12 Owner 直接 `APPROVE` 本次 linker fix，並指示未來階段內修正不得反覆停下請求 review；只在 stage exit 提出一次 review。本文件保留原始預備範圍，不表示獨立 reviewer 曾執行或核准。

## Trigger

P3 在 candidate `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` clean build 成功後，`ctypes.CDLL` 載入 `.so` 失敗：`undefined symbol: lgGpiochipClose`。

Pi raw evidence：`poc_display/evidence/m3/20260812T142812Z-ssd1351/`（Pi-local gitignored custody）。

## Identity

| Field | Value |
|---|---|
| Diff baseline | `6b24dacbca63c9f9499f86748b64a0614190c096` |
| Failed candidate | `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` |
| Replacement candidate | Owner-approved freeze commit full SHA |

## Review target

- `src/sbd/core/display/native/waveshare_ssd1351/Makefile`
- `src/sbd/core/display/native/waveshare_st7789/Makefile`
- `poc_display/tools/m3_ssd1351_capability.sh`
- `poc_display/README.md`
- `poc_display/deliveries/display_m3_contract_draft.md`
- `poc_display/deliveries/manifest_001.md`
- `docs/poc/milestone_plan.md`

Reviewer 不得修改 target files 或建立 commit；只填寫 `reviews/P1_LINKER_FIX_REVIEW_FEEDBACK.md`。

## Claimed verification

- SSD1351 dry-run link command：objects 在前，`-llgpio -pthread` 在後，並包含 `-Wl,-z,defs`。
- ST7789 dry-run link command：相同 ordering/runtime-symbol link gate。
- `bash -n poc_display/tools/m3_ssd1351_capability.sh`：PASS。
- Full display suite：`26 passed, 8 skipped`。
- `git diff --check`：PASS。

## Required review questions

1. Link order 是否可靠避免 GNU linker `--as-needed` 丟棄 `liblgpio`？
2. `-Wl,-z,defs` 是否使 unresolved native symbol 在 link time 直接 FAIL？
3. Capability packet 是否在 diagnostics 前執行並保存 `ldd -r`，failure classification 是否正確？
4. Runbook、contract、manifest、milestone 是否一致要求 Core Team user 在 exact clean target Pi build，且 `make` 成功不能取代 `ldd -r`？
5. SSD1351 與相同問題的 ST7789 修正是否有 blocking/high finding？

## Required output

將 findings、驗證命令與 `APPROVE`／`BLOCK` 寫入 `reviews/P1_LINKER_FIX_REVIEW_FEEDBACK.md`。`APPROVE` 只允許建立新 candidate；Pi build/preflight/P3 仍須由 operator 在新 SHA 重跑。
