# Display POC → Core M3 Milestone Plan

> 更新日期：2026-08-12
> 目前狀態：**P1 candidate `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` 已凍結，P2 read-only preflight PASS；下一步為 P3 Pi capability/evidence run**

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
- [x] Replacement candidate 已凍結為 `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27`；`3120c08c2b15b19c2b2b16a35577e456ad394937` 只作 reviewed baseline，不作最終 P3 target。
- [x] 整個 tracked repository snapshot 以 candidate full Git SHA 作為單一提交包，不要求逐檔 checksum。

P2/P3 必須 checkout 同一 candidate SHA。只有無法納入 Git 提交包的 Pi artifact、local config 或 raw evidence，才在產生時另記 checksum 與保管位置；不阻擋 P1 freeze。

---

## Milestone P2 — Fixture Lock and Read-only Preflight

**目的：先確認硬體、接線與執行環境，再進行會驅動 OLED 的測試。**

完成條件：

- [x] Operator 確認 SSD1351 模組、revision（無標示可記 `unmarked`）、fixture 與接線均符合選定設定；不要求照片。
- [x] 接線符合已選定 fixture/vendor pinout，且 runtime config 全部來自 local config。
- [x] 將 logical GPIO 解析為 `gpiochip0`；config hash 為 `d4780a37497906dddbddee3074d72fd2f6acec8877b118b769f9254df25d2475`。
- [x] Pi clean detached checkout 為 P1 SHA `b1f4c3e9b6487cabe9cbc164046c4b43199a8f27`。
- [x] Read-only preflight PASS：SPI node、GPIO、依賴、權限、既有 owner/process 均無衝突。

2026-08-12T14:26:24Z 已在 replacement candidate 完成 preflight PASS；本機與 Pi SHA 相同、Pi worktree clean、SPI/GPIO device present、owner none。Raw evidence：`poc_display/evidence/m3/20260812T142620Z-pretest/`（gitignored custody）。

---

## Milestone P3 — Raspberry Pi Capability and Evidence Run

**目的：在實體 SSD1351 上完成 D2–D4 所需證據。**

完成條件：

- [ ] Pi-local clean build 成功，記錄 compiler/toolchain、license、target 與 `.so` checksum。
- [ ] Lifecycle/negative-path PASS：`start → write_pixels → show → stop`、reopen、repeated stop、wrong buffer length、missing device/config、fallback/exception mapping。
- [ ] 確認每次 frame intent 僅產生一次 native `present`，`clear/write` 不會隱含 flush。
- [ ] 顏色、gradient、orientation 與邊界行為由 operator attestation 確認為 PASS。
- [ ] Performance evidence 包含 warm-up、sample count、P50/P95/max、解析度、pixel format、config hash、CPU/OS/driver。
- [ ] 分開記錄 datasheet limit、requested SPI speed 與 effective speed；不以 60 FPS 或超頻作 baseline。
- [ ] 測試前後皆證明沒有殘留 SPI/GPIO owner 或測試 process。

---

## Milestone P4 — Delivery Freeze and Core Re-review

**目的：封裝可審查、可重現的 v0.3 delivery。**

完成條件：

- [ ] Sanitized summary、raw evidence custody/checksum、config hash 與完整 manifest 齊全。
- [ ] D1–D5 disposition 全部標為 `Resolved`，且每一項可追到 code/test/evidence。
- [ ] Delivery 使用 immutable full SHA；Core Team review 的也是同一 SHA。
- [ ] Core Team 檢查 D1–D5 與 regression，沒有新的 blocking finding。
- [ ] Core Team 明確 ACK：`Accepted as M3 design input`。

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
| P1 immutable candidate | 完成：`b1f4c3e9b6487cabe9cbc164046c4b43199a8f27` | 否 |
| P2 fixture/preflight | 完成：replacement SHA read-only preflight PASS | 否 |
| P3 Pi capability/evidence | 待實機 | 否 |
| P4 Core re-review ACK | 待 P1–P3 | **是** |
| C1 Core integration acceptance | 解鎖後由 Core 執行 | 非 unblock 前置條件 |
