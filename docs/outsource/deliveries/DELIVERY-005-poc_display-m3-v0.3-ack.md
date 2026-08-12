# Core Team → POC Display Team: M3 Display HAL Contract v0.3 — Accepted as M3 Design Input

- **Delivery ID**: `DELIVERY-005-poc_display-m3-v0.3-ack`
- **Previous delivery**: `DELIVERY-004-poc_display-m3-v0.2-review`
- **POC source candidate SHA**: `5c2b6ba532a2661d5db79e27736e79890931515f`
- **POC stage-exit review commit**: `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40` (origin/dev_display_p1)
- **Decision**: `Accepted as M3 design input`
- **Review role**: Core Team Designer
- **Date**: 2026-08-12

---

## 1. 審查結論

D1–D5 全數 Resolved，無 blocking 或 high finding。

**Core Team 正式接受 `poc_display/deliveries/display_m3_contract_draft.md` (Draft v0.3) 作為 M3 Display HAL 的 design input。**

Contract 狀態維持 `Draft / Accepted as M3 design input`，不標為最終 integration acceptance。最終 M3 integration acceptance 仍待 Core Tester 驗收與 POC fixture verification 分開記錄後方可結案。

---

## 2. D1–D5 驗收結果

| Finding | 審查結論 | 依據 |
|---|---|---|
| **D1** — Python HAL lifecycle、型別與模組落點 | **Resolved** | 唯一 Protocol 位於 `src/sbd/core/display/base.py`（`async start/stop`、同步 render primitives、`buf: bytes`）；`hal/protocol.py` 改為 compatibility re-export，不重建第二套 Protocol。Host pytest `26 passed, 8 skipped` 涵蓋 mock lifecycle、repeated stop、ctypes→stub 路徑。 |
| **D2** — Native C ABI 完整性 | **Resolved** | `display.h` ABI v1：`abi_version`、`struct_size`、固定寬度型別、`DisplayStatus` enum、handle lifecycle、buffer/thread ownership、error mapping 完整。Pi clean build + `ldd -r libdisplay.so` PASS（`.so` SHA-256 `2dd44a...` 與 manifest 吻合）。 |
| **D3** — Hardware Gate / GPIO & SPI Ownership | **Resolved** | Co-I2S fixture：DC=BCM24/Board18、RST=BCM25/Board22、CE0=BCM8/Board24（SPI kernel-managed）；`cs=-1` 防止 lgpio 重複 claim CE0；preflight PASS；config SHA-256 `973229d0...` 由 manifest 與 summary 交叉記錄。 |
| **D4** — Performance Claim | **Resolved** | 移除 60 fps / `<20 ms` 承諾；baseline 4 MHz；10 warm-ups、100 samples：P50 `65.87 ms`、P95 `65.88 ms`、max `65.90 ms`；effective SPI speed 明確標示 unavailable，不由 requested speed 推論 throughput。數值合理（SSD1351 Rev 1.5 payload 下限 ~57.7 ms + overhead）。 |
| **D5** — Artifact provenance | **Resolved** | Source candidate 以完整 40-char SHA 標示；Pi-built `.so`、actual config、raw evidence 均有獨立 SHA-256；兩段式 gate（design input ACK + integration acceptance）明確分開。 |

Advisory A1（非 normative 建議）、A2（atomic 措辭）：均 Resolved。

---

## 3. 非阻擋觀察（不影響 ACK）

| # | Severity | 說明 | 建議 |
|---|---|---|---|
| F1 | `low` | `manifest_001.md` Known limits 第 142 行殘留「Primary fixture/revision operator attestation and resolved gpiochip remain pending」，與 P2/P3 實際結果矛盾。 | 次版本更新時清除。 |
| F2 | `low` | manifest 第 128 行 `PENDING_PI_RUN` 殘留，與 External Materials PASS 矛盾。 | 次版本更新時清除。 |
| F3 | `none` | `display_close` 未清除 `g_owner_thread`；因 `g_is_open` 已清零，不構成 correctness 問題。 | 可選防禦性清除。 |

---

## 4. 驗證摘要

| 驗證項目 | 結果 |
|---|---|
| D1 — `base.py` Protocol 簽名（`async start/stop`、同步 primitives、`bytes`）對齊 Ch 2a/Ch 8 | PASS |
| D1 — `hal/protocol.py` 為 compatibility re-export，無第二套 Renderer/Arbiter | PASS |
| D1 — Host pytest `26 passed, 8 skipped` | PASS |
| D2 — `display.h` ABI v1 完整性（struct、enum、lifecycle、error mapping） | PASS |
| D2 — Pi clean build + `ldd -r libdisplay.so` PASS；`.so` SHA-256 一致 | PASS |
| D3 — `profiles.py` `cs=-1` 防止 CE0 double-claim | PASS |
| D3 — Co-I2S fixture config hash 在 manifest 與 summary 一致 | PASS |
| D4 — 效能數值合理性（65.9 ms ≈ 57.7 ms payload + overhead） | PASS |
| D4 — 無 60 fps / `<20 ms` 宣稱；effective speed 未由 requested speed 推論 | PASS |
| D5 — Candidate SHA `5c2b6ba...` 在 manifest × summary × finding_disposition 三處一致 | PASS |
| D5 — Stage-exit commit `055517a` 為 source candidate `5c2b6ba` 的直接後代，無 source code 變動 | PASS |
| Makefile link order（`$^` 在 `$(LDLIBS)` 之前）與 `-Wl,-z,defs` | PASS |

---

## 5. 後續分工

| Owner | Action |
|---|---|
| **Core Team Developer** | 基於 `base.py` `DisplayDevice` 介面開發 M3 `DisplayRenderer` 與 `DisplayArbiter`，並在完成後回交 full 40-char integration SHA、環境/config、tests/evidence index 與 known limits。 |
| **Core Team Tester** | 執行 M3 integration acceptance（涵蓋 start/present/stop/reopen、錯長度、invalid device/fallback、重複 lifecycle、P50/P95；不得以 POC fixture verification 替代）。 |
| **POC Display Team** | 收到 Core integration SHA 後，在實體 Pi 5 fixture 上針對 native/hardware 邊界複驗（不重做產品 Arbiter 全面驗收）。|
| **POC Display Team** | 次版本清除 F1/F2 manifest 殘留過時描述（不阻擋本 ACK）。 |

---

> 本 ACK 依 `docs/outsource/references/README.md` 規範，記錄於 `deliveries/`，不修改 `poc_display/deliveries/display_m3_contract_draft.md` 原文。
> 本 ACK 不取代 Core Tester M3 integration acceptance，亦不取代 POC fixture final verification。
