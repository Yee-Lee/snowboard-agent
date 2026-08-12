# P4 Display POC Stage-Exit Review Feedback

狀態：`COMPLETE`

> 本檔案由獨立 reviewer process 填寫；implementation process 不代填結論。

## Review identity

| Field | Value |
|---|---|
| Reviewer/process | Antigravity AI (Claude Sonnet 4.6 Thinking) — 獨立 reviewer |
| Reviewed at UTC | `2026-08-12T15:15Z` |
| Source candidate SHA | `5c2b6ba532a2661d5db79e27736e79890931515f` |
| Stage-exit delivery SHA | `055517a905bd2c8f8531c05acfa658854e25491f` |

---

## D1–D5 Disposition Review

### D1 — Python HAL Protocol

**狀態：Resolved（code+test 可追溯）**

- [`base.py`](src/sbd/core/display/base.py) 是唯一 `DisplayDevice` Protocol；`start/stop` 為 `async`、`clear/write_pixels/show/size` 為同步，完全符合 contract §1–§2。
- [`ctypes_backend.py`](src/sbd/core/display/hal/ctypes_backend.py) `start()` 確保只在有效 handle 後建立 back buffer；`stop()` 冪等，無效 handle 不做 native close。
- `write_pixels()` 嚴格拒絕非 `bytes` 型別及錯長度，且不改動現有 buffer。
- `show()` 每次只呼叫一次 `display_present_rgb565`；`clear/write_pixels` 無 SPI I/O。
- 無第二套 Renderer/Arbiter；Compatibility module 只 re-export。
- Host test suite（26 passed, 8 skipped）涵蓋 mock lifecycle、repeated stop 與 ctypes→stub 路徑。

**結論：D1 Resolved，evidence 完整。**

---

### D2 — C ABI

**狀態：Resolved（code+Pi evidence 可追溯）**

- [`display.h`](src/sbd/core/display/native/include/display.h) ABI v1：`abi_version`、`struct_size`、固定寬度型別、完整 `DisplayStatus` enum、`display_abi_version/open/get_info/present_rgb565/close`，全部符合 contract §3。
- [`pin_config.h`](src/sbd/core/display/native/include/pin_config.h) 定義 `DisplayConfig`；`display_config_init()` 初始化所有 sentinel 值，防止未設定欄位被誤用。
- [`display_driver.c`](src/sbd/core/display/native/waveshare_ssd1351/display_driver.c) `validate_config()` 在 open 前完整驗證；`g_owner_thread` 強制 thread affinity（wrong thread → `DISPLAY_E_WRONG_THREAD`）。
- `display_close` 對 `!g_is_open` 回傳 `DISPLAY_E_NOT_OPEN`，與 contract §3.2 一致。
- **Pi evidence**：`ldd -r libdisplay.so` PASS（no undefined symbol）；`.so` SHA-256 `2dd44a...` 與 manifest 吻合；Pi clean build 由 `M3-HW-SUMMARY-2026-08-12.md` 記錄。

**結論：D2 Resolved，Pi build+ldd-r evidence 完整。**

---

### D3 — Hardware Gate / GPIO & SPI Ownership

**狀態：Resolved（config+Pi evidence 可追溯）**

- Co-I2S fixture：DC=BCM24/Board18、RST=BCM25/Board22；SPI CE0=BCM8/Board24 由 kernel `spi0 CS0` 管理，native 不再透過 lgpio claim CE0。
- [`profiles.py`](src/sbd/core/display/hal/profiles.py) `load_display_config()` 將 `cs` 設為 `-1`，避免 CE0 被 lgpio 重複 claim，正確防止 `DISPLAY_E_GPIO (-9)` 失敗。
- [`dev_config_runtime.c`](src/sbd/core/display/native/dev_config_runtime.c) `DEV_ModuleInit_WithConfig()` 只 claim DC/RST；`lg_SpiOpen()` 管理 SPI CE。
- Config hash `973229d0...` 已由 manifest 與 summary 兩處交叉記錄。
- Preflight（`20260812T145629Z-pretest`）PASS：SPI node present、GPIO owner none。
- Operator 直接確認 fixture/wiring/revision（photos not required per P1 decision）。

**結論：D3 Resolved，CE ownership 修正有效，evidence 可追溯。**

---

### D4 — Performance Claim

**狀態：Resolved（evidence 可追溯，邊界明確）**

- 移除 `60 fps` 與 `<20 ms` 承諾；contract §5 僅保證以 4 MHz baseline 量測 P50/P95/max。
- **Measured**：10 warm-ups、100 samples、P50 `65.8713625 ms`、P95 `65.879723 ms`、max `65.897834 ms`；measurement boundary 為 adapter `show()` 至 native `present` 回傳。
- 合理性：SSD1351 Rev 1.5 single pixel clock 220 ns × 32768 bytes × 8 bit/byte ≈ 57.7 ms payload 下限；觀測到的 ~65.9 ms 包含 command、GPIO、syscall overhead，數值合理且無矛盾。
- Effective SPI speed 明確標示 unavailable，未由 requested speed 推論 throughput——符合 contract §4.1 要求。
- Pi `M3-HW-SUMMARY-2026-08-12.md` 與 manifest 外部材料欄位均已記錄此邊界。

**結論：D4 Resolved，performance claim 邊界正確，無虛報。**

---

### D5 — Delivery Fix

**狀態：Resolved（candidate SHA 已固定）**

- Source candidate `5c2b6ba...`：manifest 兩處（Source identity / Submission unit）均以完整 40-character SHA 標示，不再使用 placeholder。
- Stage-exit delivery `055517a...`：僅新增 sanitized summary 與 evidence index metadata，不更動 source candidate SHA。
- 兩 SHA 間只有 5 個文件改動（milestone_plan、finding_disposition、manifest、evidence/README、HW-SUMMARY），無 source code 變動。
- Pi-built `.so`、actual config、raw evidence 均以整包 SHA-256 記錄在 manifest External Materials 欄位，符合 §6.1 要求。
- Makefile：`-Wl,-z,defs` 確保 link 時立即報告 undefined symbol；`$^` 在 `$(LDLIBS)` 之前（link order 正確）。

**結論：D5 Resolved，delivery identity 明確可追溯。**

---

## Findings

| # | Severity | File:line | Finding | Evidence / reproduction | Required action |
|---|---|---|---|---|---|
| F1 | `low` | `manifest_001.md` §Known limits | "Primary fixture/revision operator attestation and resolved gpiochip remain pending" 仍殘留於 Known limits，但實際上 P2/P3 已完成，此說明已過時。 | `poc_display/deliveries/manifest_001.md` line 142 | 次版本更新時清除；不阻擋 Core ACK。 |
| F2 | `low` | `manifest_001.md` Pi fixture packet | `Pi result/evidence index：PENDING_PI_RUN` 仍殘留於第 128 行，與 External Materials PASS 狀態矛盾。 | line 128 vs line 33–35 | 次版本更新時清除；不阻擋 Core ACK。 |
| F3 | `none` | — | `display_close` 未清除 `g_owner_thread`（close 後殘留舊值）。但 `g_is_open` 清為 0，`is_owner_thread()` 的判斷前置條件即是 `g_is_open`，因此不構成 correctness 問題。 | `display_driver.c` line 114–123 | 可選清除（防禦性）；不阻擋本階段。 |
| F4 | `none` | — | 其餘所有項目：SHA identity、ABI 匹配、config 嚴格驗證、link order、evidence boundary、disposition 表、manifest 一致性均正確。 | 見 Verification performed | 無。 |

Severity 定義：`blocking` > `high` > `medium` > `low` > `none`。

---

## Verification performed

| Command/check | Result |
|---|---|
| `git log --oneline 5c2b6ba..055517a` | PASS — 僅 1 commit（record P3 capability pass），無額外 source code 變動 |
| `git show 055517a --stat` | PASS — 5 個文件：milestone_plan、finding_disposition、manifest、evidence/README、HW-SUMMARY |
| `git show 5c2b6ba --stat` | PASS — co-I2S fixture 修正（11 個文件）；DC=24/RST=25；CE0 不再 claim through lgpio |
| `PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/ -v --tb=short` | PASS — **26 passed, 8 skipped**（8 skipped 均需 Pi/fixture） |
| `cc -std=c11 -Wall -Wextra -Werror -Isrc/sbd/core/display/native/include -fsyntax-only poc_display/tests/display_header_smoke.c` | PASS — C11 header 無錯誤 |
| Makefile link order 確認 | PASS — `$^`（objects）在 `$(LDLIBS)`（`-llgpio -pthread`）之前；`-Wl,-z,defs` 已啟用 |
| `profiles.py` `load_display_config()` CE0 handling | PASS — `cs=-1` 確保 lgpio 不 claim kernel-managed CE0 |
| `ctypes_backend.py` struct layout vs `pin_config.h` | PASS — `_CDisplayConfig` 欄位順序與 C struct 一致 |
| `display_driver.c` `validate_config()` 完整性 | PASS — 涵蓋 ABI mismatch、pixels、pins、SPI、gpio_chip、speed upper bound |
| D4 performance 數值合理性驗證 | PASS — 65.9 ms ≈ 57.7 ms payload + overhead；requested speed 未被推論為 effective throughput |
| SHA identity 一致性（manifest × summary × finding_disposition） | PASS — `5c2b6ba...` 在三份文件中一致 |
| Stage-exit delivery SHA 是否為 source candidate 的後代 | PASS — `055517a` 為 `5c2b6ba` 的直接 child commit |
| Known limits 殘留過時描述（F1/F2） | 已記錄；不構成 blocking finding |

---

## Gate conclusion

結論：**APPROVE**

沒有 `blocking` 或 `high` finding。

- **D1–D5** 均達到 `Resolved` 狀態，每一項均有可追溯的 code/test/evidence 定位。
- **Co-I2S fixture** 與 **kernel-managed CE0** 的修正確實防止了 P3 發現的 GPIO ownership 衝突（`DISPLAY_E_GPIO -9`）。
- **Delivery 可重現**：target Pi user 只需在 exact source SHA `5c2b6ba...` 執行 `make clean && make && ldd -r libdisplay.so`，不依賴 workstation native build。
- **P3 performance claims** 有明確 measurement boundary，未推論 effective SPI speed 或 FPS。
- F1/F2 為 manifest 殘留的過時文字（known limits 與 PENDING_PI_RUN），建議下一版本清除，但不阻擋 Core ACK。
- F3 為防禦性建議，無 correctness 影響。

**Core Team 可依此 APPROVE 發出 `Accepted as M3 design input` ACK。**

> 本 APPROVE 僅針對 D1–D5 disposition 與上述 review questions；不包含 C1 Core integration acceptance，亦不取代 Core Tester 驗收。
