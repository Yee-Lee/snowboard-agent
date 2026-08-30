# Snowboard Scripts

此目錄存放專案的各種自動化與維護腳本，包含但不限於開發工具、硬體驗證與測試治具。

## 硬體診斷與驗證工具 (Hardware Diagnostics)

這些腳本設計用來於 Raspberry Pi 實機上直接存取硬體介面 (HAL)，不需啟動完整的 State Manager 與 Event Bus，適合在產線組裝或除錯時快速獨立驗證外設是否正常運作。

| 腳本名稱 | 啟動捷徑 | 用途 | 互動要求 |
| :--- | :--- | :--- | :--- |
| `hw_diag.py` | `./run_diag.sh` | **全自動硬體診斷**。依序驗證音訊 (麥克風底噪、喇叭驅動)、螢幕 (SPI 通訊)、相機 (CSI 拍照)、與 GPIO (驅動綁定)。 | **無 (Zero-interaction)**，直接依賴訊號與驅動狀態判定 PASS / FAIL。 |
| `button_test.py` | `./run_button.sh` | **按鈕手動檢驗**。向核心註冊 GPIO `conversation` pin 腳位中斷，並無限期等待物理按下事件。 | **需人工按壓**。按下按鈕後會印出 SUCCESS 並結束。 |

### 執行方式

1. 進入專案根目錄或 `scripts/` 目錄。
2. 透過上述提供的 `.sh` 啟動捷徑執行。捷徑腳本會自動切換至專案根目錄並掛載 `.venv` 虛擬環境與 `PYTHONPATH` 變數。

若要直接使用 Python 執行，請確保位在專案根目錄，並帶入環境變數：
```bash
PYTHONPATH=src .venv/bin/python3 scripts/hw_diag/hw_diag.py
```
