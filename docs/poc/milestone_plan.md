# Display POC → Core M3 Milestone Plan

> 更新日期：2026-08-09
> 目前狀態：**工作準備完成；Core M3 尚未正式解鎖**

本文件以 Core Team 對 contract v0.2 的 D1–D5 review gate 為準，也是本專案判斷 Display POC 進度與下一步的唯一清單。

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

## Milestone P1 — Immutable Candidate Freeze

**目的：建立實機測試唯一可追溯的候選版本。**

完成條件：

- [ ] Host test suite 全部通過，並記錄執行結果。目前 M3 mock smoke 為 1 passed；全套 display tests 為 22 passed、8 deselected、4 setup errors，需先把 legacy `--hardware` option 從 `test_starry_night.py` 移至 `conftest.py`。
- [ ] 以完整 40-character Git SHA 凍結 candidate；worktree 必須 clean。
- [ ] Manifest 記錄 source/header/adapter/config/build inputs 的 SHA-256。
- [ ] Pi 與提交 evidence 的版本必須是同一個 candidate SHA。
- [ ] 不再使用 working-tree hash 或不同機器上的未提交內容作為證據。

---

## Milestone P2 — Fixture Lock and Read-only Preflight

**目的：先確認硬體、接線與執行環境，再進行會驅動 OLED 的測試。**

完成條件：

- [ ] 記錄 SSD1351 模組實際 revision，保留清楚的正反面與接線照片。
- [ ] 接線符合已選定 fixture/vendor pinout，且 runtime config 全部來自 local config。
- [ ] 將 logical GPIO 解析為實際 `gpiochip`，記錄 config hash。
- [ ] Pi checkout 為 P1 的 clean SHA。
- [ ] Read-only preflight PASS：SPI node、GPIO、依賴、權限、既有 owner/process 均無衝突。

---

## Milestone P3 — Raspberry Pi Capability and Evidence Run

**目的：在實體 SSD1351 上完成 D2–D4 所需證據。**

完成條件：

- [ ] Pi-local clean build 成功，記錄 compiler/toolchain、license、target 與 `.so` checksum。
- [ ] Lifecycle/negative-path PASS：`start → write_pixels → show → stop`、reopen、repeated stop、wrong buffer length、missing device/config、fallback/exception mapping。
- [ ] 確認每次 frame intent 僅產生一次 native `present`，`clear/write` 不會隱含 flush。
- [ ] 顏色、gradient、orientation 與邊界行為經人工/照片確認。
- [ ] Performance evidence 包含 warm-up、sample count、P50/P95/max、解析度、pixel format、config hash、CPU/OS/driver。
- [ ] 分開記錄 datasheet limit、requested SPI speed 與 effective speed；不以 60 FPS 或超頻作 baseline。
- [ ] 測試前後皆證明沒有殘留 SPI/GPIO owner 或測試 process。

---

## Milestone P4 — Delivery Freeze and Core Re-review

**目的：封裝可審查、可重現的 v0.3 delivery。**

完成條件：

- [ ] Sanitized summary、照片索引、raw evidence checksums、config hash 與完整 manifest 齊全。
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
| P1 immutable candidate | 待執行 | 否 |
| P2 fixture/preflight | 待實機 | 否 |
| P3 Pi capability/evidence | 待實機 | 否 |
| P4 Core re-review ACK | 待 P1–P3 | **是** |
| C1 Core integration acceptance | 解鎖後由 Core 執行 | 非 unblock 前置條件 |
