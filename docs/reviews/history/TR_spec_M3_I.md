---
requestor: "Designer"
owner: "Tester"
status: "Resolved"
---

# TR_spec_M3_I — M3 test spec coverage sign-off

- **Milestone**: M3 Raspberry Pi HAL 與硬體 bring-up
- **Review date**: 2026-08-13
- **Reviewed file**: `docs/test_spec/test_spec_M3.md`
- **External input**: `PM-OUT-260813-009-m3-display-test-spec-feedback`
- **Decision**: `APPROVED FOR DEVELOPMENT`

## Review basis

Designer 依 `docs/arch.md`、Ch 2a / Ch 8 / Ch 10、`docs/display_spec.md` 與 `docs/milestones/M3.md` 審查 Tester 規格，確認可觀察驗收覆蓋修訂後的 M3 範圍，且未把 M4c / M7 產品行為提前列為 gate。

## Finding disposition

### Blocking — M3 / M4c scope leakage

- **Basis**: M3 只接 State、Main fixture、Boot / Shutdown Blank 與底層能力；Perception / Tool / Speak、session-content setting 與 Error runtime scenario 屬 M4c。
- **Evidence**: `M3-SCN-003` 已移除；`M3-SCN-002` 的 Perception / Interrupt runtime mapping 已移除；M3 renderer template gate 不含 `main.error`；Progress / animation 不在 M3 gate。
- **Minimum acceptance**: M3 Test ID 只追 M3 requirement。
- **Disposition**: Resolved。

### Blocking — Pi hardware coverage / evidence incomplete

- **Basis**: PM-009 `OUT-M3-TEST-2026-002` 與 M3 §5.4。
- **Evidence**: 已覆蓋喇叭可聽、Camera RGB / YUV、recovery 中短按忽略、Display direction / color / flicker / latency / reopen / invalid config / cleanup；共用 RPI card 定義 full implementation SHA、硬體 / 接線、artifact、config / fixture hash、命令、操作、預期 / 實際與 artifact index。
- **Minimum acceptance**: 非 Pi portable deselection；未執行硬體卡標 Pending。
- **Disposition**: Resolved。

### Blocking — strict selected-backend config not testable

- **Basis**: Ch 10 selected SSD1351 profile 與 PM-009 `OUT-M3-DISPLAY-2026-002`。
- **Evidence**: `M3-CFG-001` table-driven 驗合法 profile、unknown / 缺值 / 矛盾 / 超規 / artifact mismatch，並證明 invalid config 未 import / dlopen / touch hardware；`M3-HAL-001` 保護 real-only lazy import。
- **Minimum acceptance**: 合法 strict parse；所有 invalid case 在硬體前以 path-aware `ConfigValueError` 拒絕。
- **Disposition**: Resolved。

## Coverage matrix

| M3 design area | Test coverage |
| :--- | :--- |
| HAL factory / fallback | `M3-HAL-001~002` |
| Audio / Camera / GPIO null, mock, real | `M3-AUD-*`、`M3-AUDI-*`、`M3-CAM-*`、`M3-CAMI-*`、`M3-GPIO-*`、`M3-GPIOI-*` |
| Display device / arbiter / renderer | `M3-DSP-*`、`M3-ARB-*`、`M3-REND-*` |
| State + Main fixture + Boot / Shutdown Blank | `M3-REND-*`、`M3-SCN-001`、`M3-DSPI-*` |
| Button semantics / recovery race | `M3-BTN-001~005` |
| SSD1351 strict config / artifact boundary | `M3-CFG-001`、`M3-HAL-001` |
| M1 / M2 regression | `M3-REG-001` |

## Sign-off

Blocking findings are resolved and no Advisory blocks development. M3 test spec coverage is approved; Developer may create `docs/reviews/dev_progress_M3.md` and estimate / split work against this signed-off revision.

This approval is not implementation acceptance. All `RPI-NATIVE` cards remain `Pending` until an exact implementation SHA is delivered and independently executed by Tester.
