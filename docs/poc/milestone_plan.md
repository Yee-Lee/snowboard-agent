# Display POC → Core M3 Milestone Plan

> 更新日期：2026-08-12
> 目前狀態：**P1–P4 completed；Core Team 已以 `DELIVERY-005-poc_display-m3-v0.3-ack` 接受為 M3 design input，Core M3 development 已解鎖**

本文件以 Core Team 對 contract v0.2 的 D1–D5 review gate 為準，也是本專案判斷 Display POC 進度與下一步的唯一清單。

## 開發與分支策略 (Branch Workflow)

- **以 OLED (SSD1351) 為優先主線**：使用 `dev_display_m{x}` 分支推進 P1~P4。不等待 LCD，取得 P4 ACK 後即可解鎖 Core M3。
- **LCD (ST7789) 為備案**：需要時從 OLED Accepted SHA 建立 `dev_display_lcd_m1`。LCD 須獨立 config/pin map；修改共用 HAL 需附 OLED regression 結果。
- **認證以 SHA 為準**：分支名稱僅為工作線，最終交付仍認完整的 40-character SHA。

## 三個狀態的定義

1. **工作準備完成**：contract、實作、測試工具、硬體 runbook 與 evidence template 已可供下一輪實機執行。
2. **Core M3 development unblocked**：D1–D5 evidence 完整，Core Team re-review 後明確 ACK：`Accepted as M3 design input`。
3. **Core M3 integration accepted**：Core Team 完成自己的抽取、整合與 Core Tester 驗收；這是解鎖之後的工作，不是 POC unblock gate。

---

## Milestone P0 — Work Preparation

**狀態：本輪完成**

- [x] DSP-01：active native 目錄具備 vendor source/header，Makefile 使用 `dev_config_runtime.c`；待 P3 以 Pi clean build 留證。
- [x] DSP-02：C header 與 driver 統一 `display_open(const DisplayConfig *)`，runtime config 不被忽略。
- [x] DSP-03：初始化失敗會釋放已取得資源，vendor 版本與授權已有記錄。
- [x] DSP-04：HAL 對齊 `start/stop/clear/write_pixels/show/size`；只有 `show` flush。
- [x] DSP-05：公開介面不再採用舊 async `present()` 模型；局部 present 不是公開契約。
- [x] DSP-09（M3 範圍）：`--display-config` 位於 `conftest.py`，mock 與 Pi marker 已備妥。
- [x] v0.3 authoritative async lifecycle contract、strict config、mock/null fallback 與 host-side checks 已備妥。
- [x] Raspberry Pi preflight、capability packet、diagnostics 與 evidence template 已備妥。
- [x] 實機測試方法採用同一 clean SHA、前後 owner 檢查、明確 PID cleanup、raw/sanitized evidence 分離。

**P0 不代表解鎖**：目前尚未執行實機連線驗證、尚未凍結 immutable delivery SHA，也尚未取得 Core ACK。

---

## Milestone P0.5 — D1-D5 Contract Remediation (v0.3)

**目的：解決 Core Team 針對 v0.2 提出的 Blocking Issues，以便順利凍結版本。**

**狀態：已放行；硬體證據與 Core ACK 分別由 P2–P4 收斂。**
完成條件 (Coding & Config)：

- [x] **D1 (Python HAL)**：修正 Protocol，`start/stop` 改為 `async`，`clear/write_pixels/show/size` 為同步。不自建 UI 狀態機。
- [x] **D2 (C ABI)**：定義明確的 C struct (config)、錯誤碼 (error enum) 與 Python 例外映射。`clear/write` 只改 back-buffer，`show` 才 flush。
- [x] **D3 (Hardware Gate)**：接線以 SSD1351 OLED 為唯一基準，修正 BCM 腳位設定，清理 config 確保能以 config hash 追溯。
- [x] **D4 (Performance Claim)**：移除無根據的 `60 fps` 與 `<20ms` 效能承諾，等待實機測試真實 P50/P95。
- [x] **D5 (Delivery Fix)**：修正 Makefile 依賴以確保 Clean Build；tracked delivery 以完整 Git SHA 作整包識別，只有無法上傳的外部內容另記 checksum／custody。

P0.5 交付原則 (依據 DELIVERY-004 規定)：
- [x] **維持 Draft 狀態**：v0.3 保持 Draft，**不由 POC 自行標記為 Accepted**。
- [x] **提供 finding disposition 表**：D1–D5 已附 code/test 定位與剩餘 Pi evidence。

**P4 exit gate**：D1–D5 disposition 全部成為 `Resolved`，且 Core Team 發出 `Accepted as M3 design input`；兩者不屬於 P0.5 前置條件。

---

## Milestone P1 — Immutable Candidate Freeze

**目的：建立實機測試唯一可追溯的候選版本。**

完成條件：

- [x] Host test suite 全部通過並記錄結果：2026-08-12 全套 display tests 為 26 passed、8 skipped；Python compile、service/mock、C11 header 與 stub-linked native ABI smoke 均 PASS。
- [x] 原始 host gate 已由獨立 process reviewer `APPROVE`；review baseline 為 `3120c08c2b15b19c2b2b16a35577e456ad394937`。
- [x] Owner 於 2026-08-12 直接 `APPROVE` 照片 gate → operator attestation 小幅變更，並明確免除第二次獨立 review；不將此決策誤記為 reviewer 結論。
- [x] Candidate `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` 曾凍結並完成 P2，但 P3 證明其 `.so` 有 unresolved `lgpio` symbol，因此不得作最終 P3 target。
- [x] Owner 於 2026-08-12 直接 `APPROVE` native link-order 與 runtime-symbol gate 修正，並指示只在 stage exit 請求 review。
- [x] Linker-fix candidate `7c3d355b3850d01ebd967186f1ee578a97108aa3` 在 Pi build/`ldd -r` PASS，但 P3 發現其 fixture config 使用錯誤的官方 DC/RST mapping，且 runtime 重複 claim SPI CE0；不得作最終 P3 target。
- [x] Co-I2S/DC-RST/CE ownership 修正後 replacement candidate 為包含本紀錄的 freeze commit；交接時回報其 full SHA。
- [x] 整個 tracked repository snapshot 以 candidate full Git SHA 作為單一提交包，不要求逐檔 checksum。

P2/P3 必須 checkout 同一 candidate SHA。只有無法納入 Git 提交包的 Pi artifact、local config 或 raw evidence，才在產生時另記 checksum 與保管位置；不阻擋 P1 freeze。

---

## Milestone P2 — Fixture Lock and Read-only Preflight

**目的：先確認硬體、接線與執行環境，再進行會驅動 OLED 的測試。**

完成條件：

- [x] Operator 確認 SSD1351 模組、revision（無標示可記 `unmarked`）、fixture 與接線均符合選定設定；不要求照片。
- [x] 接線符合已選定 fixture/vendor pinout，且 runtime config 全部來自 local config。
- [x] Co-I2S fixture 為 DC=BCM24/Board18、RST=BCM25/Board22；logical GPIO 解析為 `gpiochip0`；更新後 actual config hash 為 `973229d06ae7c2734e96ce350365e61d64e2074b47166497a09976e38246d679`。
- [x] 歷史 candidate `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` 曾 clean detached checkout。
- [x] 歷史 candidate read-only preflight PASS：SPI node、GPIO、依賴、權限、既有 owner/process 均無衝突。
- [x] Pi clean detached checkout 為 co-I2S candidate SHA `5c2b6ba532a2661d5db79e27736e79890931515f`。
- [x] 新 P1 SHA read-only preflight PASS：2026-08-12T14:56:33Z；SPI/GPIO present，owner none，Pi worktree clean。

2026-08-12T14:26:24Z 已在 `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` 完成 preflight PASS；`7c3d355b3850d01ebd967186f1ee578a97108aa3` 也曾 preflight PASS，但兩者不符合最終 co-I2S/CE ownership 修正，新的 candidate 必須重跑。Raw evidence：`poc_display/evidence/m3/20260812T142620Z-pretest/`、`20260812T144113Z-pretest/`（gitignored custody）。

---

## Milestone P3 — Raspberry Pi Capability and Evidence Run

**目的：在實體 SSD1351 上完成 D2–D4 所需證據。**
2026-08-12 首次 packet 在 `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` clean build 後載入 `.so` 失敗：`undefined symbol: lgGpiochipClose`。原因是 `-llgpio` 位於 objects 前被 linker `--as-needed` 丟棄；raw evidence：Pi `poc_display/evidence/m3/20260812T142812Z-ssd1351/`。SPI/GPIO owner cleanup PASS。
2026-08-12 第二次 packet 在 `7c3d355b3850d01ebd967186f1ee578a97108aa3` 的 Pi build/`ldd -r` PASS 後，`display_open` 回 `DISPLAY_E_GPIO (-9)`。診斷確認 CE0=BCM8 已由 kernel `spi0 CS0` 擁有，且 actual config 錯用官方 DC=25/RST=27；owner 已確認 co-I2S 為 DC=24/RST=25。修正後 native 只 claim DC/RST，SPI CE 由 device handle 管理。



完成條件：

- [x] target Pi 登入使用者在 exact clean candidate SHA 執行 clean build；`ldd -r` 無 undefined symbol；`.so` SHA-256 為 `2dd44a17abd57a195674ddcf12717bbb2759580e81bbf194723507232ad50493`。
- [x] Lifecycle/negative-path PASS：start/present/stop、reopen 3/3、repeated stop、wrong buffer length、missing SPI device。
- [x] 每次 frame intent 僅一次 native `present`；black/white/red/green/blue/gradient 均 presented。
- [x] Owner 確認顏色、gradient、orientation 與 flicker 均 PASS。
- [x] Performance evidence：10 warm-ups、100 samples、P50 65.8713625 ms、P95 65.879723 ms、max 65.897834 ms；RGB565 MSB-first、128×128、config hash 已記錄。
- [x] Requested SPI speed 4 MHz；effective speed unavailable，未推論為 measured throughput。
- [x] 測試後 SPI/GPIO owner none、Pi worktree clean；capability packet PASS。

---

## Milestone P4 — Delivery Freeze and Core Re-review

**目的：封裝可審查、可重現的 v0.3 delivery。**

完成條件：

- [x] Sanitized summary、raw evidence custody/checksum、config hash 與完整 manifest 齊全。
- [x] D1–D5 disposition 全部標為 `Resolved`，且每一項可追到 code/test/evidence。
- [x] Independent stage-exit reviewer 審核 source `5c2b6ba532a2661d5db79e27736e79890931515f` 與 delivery `055517a905bd2c8f8531c05acfa658854e25491f` 後 `APPROVE`；沒有 blocking/high finding。

- [x] Delivery 使用 immutable source SHA `5c2b6ba532a2661d5db79e27736e79890931515f`；Core Team ACK 同時記錄 stage-exit commit `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40`。
- [x] Core Team 檢查 D1–D5 與 regression，沒有新的 blocking/high finding。
- [x] Core Team 於 2026-08-12 以 `docs/pm_handoff/DELIVERY-005-poc_display-m3-v0.3-ack.md` 明確 ACK：`Accepted as M3 design input`。

**達成 P4 後，才算正式 unblocking Core M3 development。**

---

## Milestone C1 — Core M3 Integration Acceptance

**Owner：Core Team；在 P4 解鎖後進行。**

- [ ] 將 accepted POC SHA 中的 native/adapter 抽取到 Core owned path。
- [ ] DSP-06：實作 `DisplayRenderer.validate/render` 與六個 Baseline templates：`status.text`、`status.state`、`main.text`、`main.progress`、`fullscreen.text`、`fullscreen.blank`。
- [ ] DSP-07：bundle 固定字型，中文與長字串按 pixel width 換行或截斷。
- [ ] DSP-08：runtime render/HAL failure 由 arbiter latch disabled，不影響 session 或 exit code。
- [ ] DES-01：在 Ch 2a 固定 backend、HAL/native 映射、格式、rotation、驗證與 build 規則。
- [ ] DES-02：在 Ch 5 定義 device → renderer → arbiter → owners 資源圖、fallback 與 reverse stop。
- [ ] DES-03：在 Ch 8 補 injection、Baseline renderer factory、lifecycle owner 與 failure latch。
- [ ] DES-04：在 Ch 10 定義 strict display/SPI/GPIO schema 與 cross validation。
- [ ] DES-05：在 display spec 固定三區 layout、字型、換行/截斷、progress 與靜態開關機畫面。
- [ ] DES-06：在 M3 milestone 納入 selected profile、clean build、real-to-null、atomic flush、Baseline 與 Pi 驗收。
- [ ] DES-07：受影響 implement 章節完成 review gate。
- [ ] DES-08：維護 Core M3 gate、blocker、owner、下一動作與定案狀態。
- [ ] 整合 real/mock/null display、Renderer/Arbiter profiles/templates 與 Core tests。
- [ ] 在 Core target Pi 完成 Core Tester 驗收。

此 milestone 不需要先完成，才能宣布 POC 已解除 Core M3 development blocker。

如主要面板改為 ST7789、引入獨立 process/IPC、公開 async service、overlay/preemption/fullscreen queue 或新 Display role，必須先交 Architect review。上述能力以及 animation、video、touch、LED、OSD 均不屬 M3。

---

## Unblock 判定

| Gate | 本輪狀態 | 是否足以解鎖 Core M3 |
|---|---|---|
| P0 工作準備 | 完成 | 否 |
| P0.5 D1–D5 coding/config remediation | 已放行 | 否 |
| P1 immutable candidate | 完成：`5c2b6ba532a2661d5db79e27736e79890931515f` | 否 |
| P2 fixture/preflight | 完成：co-I2S candidate preflight PASS | 否 |
| P3 Pi capability/evidence | 完成：capability packet PASS、operator visual PASS | 否 |
| P4 Core re-review ACK | 完成：`DELIVERY-005-poc_display-m3-v0.3-ack`，Accepted as M3 design input | **是** |
| C1 Core integration acceptance | 解鎖後由 Core 執行 | 非 unblock 前置條件 |
