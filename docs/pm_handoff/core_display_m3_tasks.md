# 核心團隊 Display M3 任務

對象：核心產品團隊與主線產品開發團隊
Owner：內部 Designer
狀態：Ready for PM delivery；不代表 PM 已交付

## 結論

POC repo `display` / `cf64039507090a8ce76d769412ad43092496f9c3` 只作候選來源，不整包合併。M3 依現行產品契約實作同步 `DisplayDevice` -> `DisplayRenderer` -> `DisplayArbiter` -> `owners`，只交付靜態 Baseline。

POC 的 `DisplayService`、`async present()`、`queue`、`IPC`、`overlay`、`animation` 與 `video` 不屬 M3；若未來採用，另走 M7 或 Architect review。

## CORE-DSP-01：固定 M3 進場基線

Owner：User / Designer / Architect ( 必要時 )

- M3 只能引用活動產品 repo 明確 Accepted 的 M2 完整 SHA；歷史 `snowboard-agent/` M2 不算現行基線。
- 選定單一目標面板、chip、resolution、orientation、pixel format 與接線。
- 現行架構以 OLED 為主；若改用 ST7789 LCD 或引入 IPC / I/O thread / preemption，先交 Architect 裁定。
- 接線須與 Audio 共存；目前 LCD 預設 BL GPIO18 與 I2S BCLK 衝突，必須先重新配置或放棄該 profile。

驗收：產品 dashboard 記錄 accepted M2 SHA、選定硬體、pin map 與 architecture decision。

## CORE-DSP-02：固定產品契約與文件

Owner：Designer / 主線開發團隊 / Reviewer

- 以產品 repo 的 `docs/arch.md` 為唯一架構來源；POC `display_arch.md` 不取代它。
- 修訂 Ch 2a / 5 / 8 / 10，固定 selected chip、strict config、resource graph、NullDisplay、failure latch 與 lifecycle。
- 建立產品 `docs/display_spec.md` Baseline：固定字型、三區域、換行 / 截斷及六個 templates。
- 六個 templates：status text、status state、main text、main progress、fullscreen text、fullscreen blank。

## CORE-DSP-03：重構 Renderer 與裝置抽象

Owner：主線產品開發團隊

- 從 POC Accepted SHA 抽取 selected native driver、C ABI、ctypes wrapper 與 RGB565 converter，再適配產品契約。
- Native library 依 chip 收納；Pi-only import lazy，`.so` 路徑、SPI、GPIO 與 rotation 只由 strict config 提供。
- 實作 real / mock / null factory；real 建立或 start 失敗時清理 partial resource，再注入 NullDisplay 並設 `capability=false`。
- 實作 deterministic Baseline renderer、固定離線字型、buffer length / byte order / rotation 驗證。
- 接上 RM resource graph、Presenter、StatusBar、startup / shutdown fullscreen owner。
- Renderer / HAL runtime failure 只 latch Display disabled，不發布 `ErrorOccurred`、不改 session 或 exit code。

驗收：產品 unit / integration tests 覆蓋 atomic render、ownership、null fallback、failure latch 與 reverse stop。

## CORE-DSP-04：完成 M3 Pi 驗收

Owner：主線產品開發團隊 / Tester

- Pi 5 clean build selected native library，記錄 compiler、lgpio、config hash 與 `.so` checksum。
- 驗證解析度、orientation、color / byte order、clear / write / show、open-close 與 invalid-device fallback。
- 驗證六個 Baseline templates、固定字型可讀性、fullscreen ownership 與 startup / shutdown。
- 完整軟體 regression 與 M3 Pi test 均通過；人工畫面檢查不能取代 buffer / call-order 自動測試。

驗收：Tester 依產品 delivery exact SHA 確認 evidence；團隊自驗不等於 Accepted。

## M3 不包含

- 星空、fade、chat、video、正式動畫或 30 FPS 目標。
- Display process / IPC、scheduler、frame queue、overlay、preemption、touch、LED 或 OSD。
- 將 POC repo 的 service / API / tests 直接搬入產品 repo。

## 主線交付要求

主線團隊須在產品 repo 的 `docs/reviews/outsource/` 提交 delivery manifest、POC handoff 引用、架構變更聲明、tests / Pi evidence 與完整 commit SHA。
