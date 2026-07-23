# Snowboard Agent

離線 AI 語音助理，執行於 Raspberry Pi 5 (Pi OS)。

> **狀態**：POC 開發中。架構詳見 [`docs/arch.md`](docs/arch.md)、實作階段見 [`docs/milestone.md`](docs/milestone.md)。

---

## 系統概觀

- **端側運算**：ASR / LLM / TTS 全在本地執行
- **事件驅動**：模組互不相識，全靠 event bus 與 state manager 溝通
- **生命週期分層**：`wake → perception → brain → action` + `adaptor` 全程訂閱 + `core` 提供硬體 HAL 與基礎設施

## 硬體

- I2S 麥克風、I2S 喇叭
- SPI OLED
- 8MP CSI 相機
- GPIO（按鈕、LED、家電控制）

## 目錄結構

```
snowboard-agent/
├── src/sbd/
│   ├── core/           基礎設施 + 硬體 HAL（event_bus、state_manager、config、audio、display、camera、gpio）
│   ├── wake/           觸發層（voice / button / event）
│   ├── perception/     感知層（listen / read / look）
│   ├── brain/          認知層（reasoner + LLM + prompt_builder）
│   ├── action/         行動層（speak / tool）
│   ├── adaptor/        外部工具 / 狀態具現化（display / leds / external_broker）
│   └── main.py         組裝與啟動
├── tests/              純邏輯單元測試
├── scripts/            人手動跑的工具
├── models/             模型權重（gitignored）
└── docs/
    ├── arch.md         架構文件（權威）
    ├── milestone.md    實作計畫（M1–M5+）
    └── arch_obsoleted.md
```

## 快速啟動

需要 Python 3.11+（Windows 下用 `py -3.11`；RPi5 用 `python3.11`）。

```bash
# 安裝（開發模式 + 測試相依）
py -3.11 -m pip install -e ".[dev]"

# 跑測試
py -3.11 -m pytest -v

# 啟動 backbone（M1）
py -3.11 -m sbd.main
```

## 開發階段

| 階段 | 目標 | 硬體 | AI |
|---|---|---|---|
| M1 | Event Bus + Protocol + StateManager | ❌ | ❌ |
| M2 | Mock Pipeline 走通六狀態 | ❌ | ❌ |
| M3 | 硬體 HAL 上線 | ✅ | ❌ |
| M4 | 真實 AI 模型接入 | ✅ | ✅ |
| M5+ | 擴充功能（wake word、YOLO、MQTT、多輪、部署） | ✅ | ✅ |

目前完成 M1，詳見 [`docs/milestone.md`](docs/milestone.md)。
