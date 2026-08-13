# Response: OUT-M3-REVIEW-2026-001

- **Handoff ID**: `PM-OUT-260813-009-m3-display-test-spec-feedback`
- **Feedback ID**: `OUT-M3-REVIEW-2026-001`
- **Status**: `Revised — internal coverage sign-off complete; external submission pending user-approved commit`
- **Candidate branch**: `dev_agent_m3`
- **Comparison baseline**: `61a17005de6076a3b79a4598cabd89be8b363e33`
- **Delivery commit SHA**: `Not created — project policy requires USER confirmation before git commit`
- **Prepared delivery**: `DELIVERY-M3-DESIGN-TEST-001`
- **Architecture change**: `No`
- **Scope**: Design / Test-spec only — Implementation SHA: `N/A - design/test-spec only`

---

## Finding Disposition

### `OUT-M3-DISPLAY-2026-002` — Blocking — strict config 未定義完整

**Disposition**: Resolved

- Ch10 已定義 artifact path / SHA-256、ABI v1、SPI0 CE0、DC/RST、rotation 0、RGB565 MSB-first 與 32768-byte full-frame schema；Pi fixture 值只由 local deployment config 提供。
- Ch 2a 與 M3 milestone 已固定 real-only lazy import / pre-hardware validation boundary；`M3-CFG-001` 已改為 table-driven strict parse / contradiction / over-limit / no-hardware-touch 驗收。

---

### `OUT-M3-TEST-2026-002` — Blocking — M3 範圍與硬體覆蓋不正確

**Disposition**: Accepted — 已修訂 `docs/test_spec/test_spec_M3.md`

逐點處理如下：

#### 移出 M4c 的項目

| 項目 | 原測項 | 處理 |
|---|---|---|
| Session content setting | `M3-SCN-003` | **已刪除**；`SET-SHOW-SESSION-CONTENT` 屬 M4c，不進入 M3 test gate |
| Progress template 技術預留驗證 | `M3-REND-003` 內 `main.progress` 斷言 | **已移除**；M3 不驗 Progress 產品能力，`main.progress` 預留由 Designer 另行規劃 |

#### 改驗公開 observable 結果

| 項目 | 原測項 | 處理 |
|---|---|---|
| `_rendering_enabled` private field | `M3-ARB-004` | **已修改**：改以 `MockDisplay.show()` call count 驗證 degraded 行為，不檢查 private 欄位 |

#### 補齊 M3 Pi 測項

| 新測項 | 補充內容 | 依據 |
|---|---|---|
| `M3-BTN-005` | Recovery 進行中短按被忽略 | `milestones/M3.md` §5.4 Button 語意 |
| `M3-AUDI-003` | 喇叭可聽人工 checklist（含 fixture SHA / config hash / 硬體型號 / pass-fail） | `milestones/M3.md` §5.4 §3 |
| `M3-CAMI-003` | Camera real RGB / YUV capture 格式與尺寸驗收 | `milestones/M3.md` §5.4 item 2 |
| `M3-DSPI-004` | Display reopen 與 native handle / GPIO / SPI / thread cleanup | Ch 8 §9；Ch 2a §2a.3 |
| `M3-DSPI-005` | rotation 0、RGB565 MSB-first、可讀性與 flicker 人工 card | `milestones/M3.md` §5.2.2 / §5.4 |
| `M3-DSPI-006` | 100-frame raw latency、P50 / P95 / max，不虛構 FPS | `milestones/M3.md` §5.4 |
| RPI card contract | hardware / wiring、full SHA、artifact、config / fixture hash、命令、操作、預期 / 實際與 artifact index | `test_spec.md` §2.1 / §2.3；`test_spec_M3.md` §3 |

所有新增 Pi 測項對應 `milestones/M3.md` §5.4 之既有驗收要求，**非追加設計文件外的額外邊界條件**。
未執行的 Pi 項目標記 `Pending`，不宣稱 milestone Accepted。

---

### `OUT-M3-DSP-2026-005` — High — Spec、trace 與 mock 不一致

**Disposition**: Resolved

- `CMP-ANIMATION`、`SCN-BOOT-ANIMATION`、`SCN-SHUTDOWN-ANIMATION` 已補回 stable ID 並明標 M7 Deferred；不進入 M3 implementation / test gate。
- `DSP-REQ-001~009` 已補 milestone 與 approval owner / evidence trace。
- Error mock 的 Status 改用 foreground state style，Main 只顯示 error-style sanitized summary，不重複「錯誤」；M3 renderer gate也已排除 M4c `main.error` runtime scenario。

---

### `OUT-M3-DELIVERY-2026-001` — Blocking — 缺正式 exact-SHA 交付

**Disposition**: Prepared；external exact-SHA submission remains Blocking until the user-approved commit exists

- 本 Response 文件為 `docs/outsource/responses/OUT-M3-REVIEW-2026-001.md`
- Delivery：`docs/outsource/deliveries/DELIVERY-M3-DESIGN-TEST-001.md`
- Evidence：`docs/outsource/evidence/DELIVERY-M3-DESIGN-TEST-001/README.md`（Pi cards 全部 `Pending`）
- 本輪為 design / test-spec only；Implementation SHA = `N/A - design/test-spec only`
- 未執行 Pi 項目一律標 `Pending`，不宣稱 implementation 或 milestone Accepted
- 專案 workflow 禁止未經 USER 明確同意執行 commit；取得同意並建立單一候選 commit 後，才可提供完整 40-character HEAD 給 PM intake。文件不偽造或預測 commit SHA。

---

## Designer sign-off

- `TR_spec_M3_I`: `Resolved`；M3 test spec 100% 覆蓋修訂後的 M3 design / milestone，M4c / M7 項目未進 M3 gate。
- Internal development gate：`APPROVED`；Developer 可建立 `dev_progress_M3.md` 並依已簽核 spec 拆包。
- External PM intake：`PENDING COMMIT SHA`；這不等同硬體 acceptance，所有 RPI cards 仍為 Pending。
