# M2 開發與驗收 Runbook

本文件說明如何操作與驗收 M2（Mock 對話垂直切片）；驗收行為與 Pass gate 以 [`test_spec_M2.md`](../test_spec/test_spec_M2.md) 與 [`milestones/M2.md`](../milestones/M2.md) 為準。

## 範圍

M2 是完整 Mock 對話流程的垂直切片驗證，包含：
- Mock/Null HAL (Audio, Display, Camera, GPIO) 與 lazy factory
- Deterministic Workers (Listen, Read, Look, Reasoner, Speak, Tool, Rest)
- External Message Ingestion、Buffer 與 Read Window
- Action Payload Validation 與 ToolRegistry
- 兩種主要 Session Flow (Wake/Button Session 與 External Message Session)

## 建立開發環境

需求：Python 3.11 以上。

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python --version
```

Windows 啟用環境時使用 `.venv\Scripts\activate`。

## 執行測試

在專案根目錄下執行以下驗收測試：

```bash
python -m pytest -v tests/milestones/test_m1_foundation.py
python -m pytest -v tests/milestones/test_m2_mock_pipeline.py
python -m pytest -v
```

三條命令均須通過，且 M1 及 M2 對應測試不得使用 skip 或 xfail。

## 本機啟停 Smoke

```bash
python -m sbd.main
```

使用預設的 Repository Default Mock Config 啟動，看到 Sanitize IDLE log 後按 `Ctrl+C` (SIGINT)；正常 shutdown 的 process exit code 應為 `0`。

Exit code 判定表：

| Code | 意義 |
|---:|---|
| 0 | 正常關機 |
| 2 | Config 錯誤 |
| 3 | Startup 錯誤 |
| 4 | Runtime fatal |

## M2 不包含 (Non-goals)

- 不安裝或呼叫真實 Raspberry Pi HAL、ASR、TTS、Vision、LiteRT-LM
- 不連接實體硬體 (OLED、CSI 攝影機、實體 GPIO 電氣行為)
- 不連接真實 MQTT broker
- 不建立語音喚醒 daemon (Voice-wake signal 由 mock InputSource 產生)
- 不依賴使用者 Credential、網路或外部模型檔
