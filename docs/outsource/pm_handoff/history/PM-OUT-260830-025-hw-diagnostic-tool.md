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

