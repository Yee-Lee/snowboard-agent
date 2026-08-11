# Display POC 團隊修訂與交付任務

對象：Display POC 團隊
Owner：內部 Designer
狀態：Ready for PM delivery；不代表 PM 已交付

## 結論

現有 repo `display` / `cf64039507090a8ce76d769412ad43092496f9c3` 已收到，但尚無 delivery manifest 或 evidence，因此不是 POC Accepted。

POC 團隊只需交付可重現的 selected panel driver、HAL adapter 與 Pi 驗證；不需把既有 `DisplayService` 架構改成主線產品，也不負責產品 RM、Arbiter、Baseline templates 或主線接線。

## POC-DSP-01：補正正式 delivery

- 在 `poc_display/deliveries/` 提交 Delivery ID、repo、branch、完整 SHA、環境、硬體、命令、結果、evidence 路徑及已知限制。
- 在 `poc_display/evidence/` 建立對應索引。
- 後續修訂使用完整 SHA；聊天、照片或 branch HEAD 不取代 delivery。

驗收：內部可依 manifest checkout 指定 SHA 並重現 smoke / build / Pi diagnostics。

## POC-DSP-02：完成 selected panel 的 clean native build

前置：核心團隊先固定 selected panel 與 pin map；未選面板可保留為 rejected / unverified candidate，不要求同時產品化。

- 把 build 所需 vendor `.c` / `.h`、runtime config source、Makefile 與 license / revision 完整提交。
- 現有兩個 active Makefile 引用未提交的 `DEV_Config.c` 與 panel source，必須修正到 clean checkout 可 build。
- Build 不得依賴 archive 目錄、未追蹤檔案或開發者絕對路徑。
- 提交 compiler、lgpio version、clean build 命令與 `.so` checksum。

驗收：Pi 5 從 clean checkout 產生 selected `libdisplay.so`。

## POC-DSP-03：修訂 C ABI 與 runtime config

- 補齊並收斂 C ABI 導出，定義穩定強型別 struct、enum 與錯誤碼。
- strict config 必須支援外部傳入 SPI device、bus / cs、speed_hz、DC / RST / BL pins、resolution、orientation、byte order、buffer size 與 rotation。
- invalid config、GPIO 或 SPI 初始化失敗時即時回傳明確錯誤，並釋放已取得資源。
- `open` -> `clear` / `write` / `show` -> `close` 可重複執行，無 GPIO、SPI 或 native handle 殘留。
- 明確固定 RGB565 byte order、buffer length、resolution 與 rotation owner。

驗收：正常、bad config、missing device、重複 open-close 均有可重現結果。

## POC-DSP-04：提供主線可適配的最小 HAL

- 保留 selected ctypes / native wrapper，但提供對產品 `start/stop/clear/write_pixels/show/size` 的映射說明或薄 adapter。
- `clear/write_pixels` 只更新 back buffer，`show` 才 flush；buffer length 不符直接失敗。
- Pi-only dependency 維持 lazy；mock smoke 不載入 lgpio 或 native library。
- POC 的 async `open/present/close`、service、queue、IPC、animation 與 video 標示為未採用，不列入 M3 handoff。

驗收：固定 buffer 可完成一次 atomic clear / write / show，且 adapter 邊界與產品 Ch 2a 無矛盾。

## POC-DSP-05：完成 Pi 5 硬體驗證

- 記錄 panel / chip / resolution / orientation / pixel format、實際 pin map、SPI speed、Pi OS 與測試時間。
- 修正 README、profile defaults 與 official-test pin map 的矛盾；若使用 LCD，不得與 Audio I2S GPIO18 衝突。
- 執行 black / white / RGB / gradient / clear / open-close 與 invalid-config diagnostics。
- 記錄 full-frame flush p50 / p95 / max、可用 SPI speed、顏色 / 方向及閃爍觀察。
- Evidence 不含 secret、絕對使用者路徑或未授權 vendor artifact。

驗收：Tester 可依同一 SHA、config 與命令在相同硬體重現結果。

## 最終 handoff

- Selected panel 的 source、ABI、adapter、build、license、hardware manifest、diagnostics 與效能摘要。
- Rejected / unverified panel、POC 進階架構與已知限制清單。
- 明確說明哪些檔案可供主線抽取，哪些 demo / service / animation 不應移植。

提交完成隻代表 `Ready for internal review`。Blocking findings 關閉且 Tester / Reviewer 確認後，Designer 才能建立 POC handoff；不等於主線 M3 完成。
