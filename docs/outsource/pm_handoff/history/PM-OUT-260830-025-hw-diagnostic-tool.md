---
requestor: "USER"
owner: "Designer"
status: "Resolved"
---

# Hardware Diagnostic Tool Requirement

## 1. 需求背景 (Context)

因應接下來硬體組裝異動等流程，需要一個獨立、輕量、能夠快速驗證外設（Hardware Peripherals）正常運作的測試工具。該工具需提供：
- 快速收音 (Audio Record)
- 播音 (Audio Playback)
- Display 顯示 (OLED)
- Camera 拍照 (CSI Camera)
- GPIO 按鈕生效等

## 2. 需求範圍 (Scope)

- 該工具應為單一可獨立執行的腳本（放置於 `scripts/hw_diag.py`）。
- 應避開主對話流程（SM / EventBus / MQTT 等），直接調用底層 HAL (Hardware Abstraction Layer)。
- 在互動介面上，引導維修/組裝人員依序觸發測試與觀察結果。

## 3. 對應行動 (Action)

- **Designer**：接受此需求，視為 `chore` / `feat`（硬體診斷工具），不影響既有 M1-M5 里程碑之主要產品架構，並同意將其置入 `scripts/hw_diag.py`。
- **後續實作**：由 Designer 交付測試腳本。

## 4. Implementation correction（2026-08-30）

USER確認`hw_diag`必須維持全自動，實體conversation button另由`run_button`處理。Current Core
implementation因此收斂為：

- `scripts/hw_diag.py`：zero-interaction runner。Audio播放0.5秒固定440 Hz tone並由產品mic回錄比較
  baseline/tone能量；Camera驗format／size／非單色luma；GPIO自動驗gpiochip access與設定中的
  conversation input line request／release；Display驗artifact、ABI與兩次SPI present transaction。
- GPIO不要求jumper或人工按鍵；沒有電氣回授時只claim driver/line transaction，不claim實體pin電位或
  button circuit PASS。實體conversation button另由`run_button.py`處理。
- SSD1351沒有panel readback，automated結果明記`visual panel unverified`，不得將SPI成功改寫為肉眼
  顯示PASS。
- `scripts/run_button.py`：獨立、bounded manual conversation-button diagnostic；未按或timeout為non-zero，
  不併入automated summary。
- `tests/test_pm_025_hw_diag.py`：以injected HAL覆蓋tone threshold、silence false-pass、Camera uniform
  rejection、GPIO missing-config／line request success／failure、Display failure cleanup與manual button separation。
- config只由caller以`--config`提供；工具不再hard-code device、format、ABI或pin，也不寫formal
  acceptance evidence。
- `scripts/hw_diag/run_diag.sh`只負責使用repo `.venv`啟動Python CLI並轉交參數，不隱式選擇config。

## Operator convenience refinement（2026-08-30）

USER後續要求將工具集中並移除日常參數輸入。Current Core將Python工具移至
`scripts/hw_diag/hw_diag.py`與`scripts/hw_diag/run_button.py`，並提供零參數
`scripts/hw_diag/run_diag.sh`及`scripts/hw_diag/run_button.sh`；兩個wrapper在caller未指定
`--config`時使用repo root的`config.m3.local.yaml`。此follow-up取代本單上方的原始path與
caller必須明確提供config之操作要求，但不改變zero-interaction與manual button分離邊界。

本修正不改產品HAL／架構，也不產生formal Pi acceptance；實機執行方式見`scripts/README.md`。
