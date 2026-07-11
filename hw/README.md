snowboard-agent

snowboard-agent/
├── main.py                # 系統大腦入口：初始化模組、播放動畫並進入主狀態機迴圈
├── config/                # 系統設定檔 (GPIO 腳位、模型路徑、喚醒詞)
├── core/                  # 認知中樞
│   ├── agent.py           # 狀態機管理 (Booting -> Idle -> Listening -> Thinking -> Speaking)
│   └── personality.py     # System Prompts (精簡、幽默、歪理邏輯)
├── ai/                    # AI 模型抽象層 (ASR, LLM, TTS, Vision)
├── hw/                    # 硬體驅動層 (LED, LCD, Audio, Camera)
├── tests/                 # 獨立測試腳本 (單獨測試聽覺、大腦或發聲，免啟動主程式)
├── assets/                # 靜態資源 (LCD 開機動畫、系統提示音)
├── requirements-core.txt  # 跨平台共用依賴 (PC & RPi)
└── requirements-rpi.txt   # RPi 專屬硬體驅動依賴


🚀 快速啟動 (Getting Started)

開發環境設置 (PC 端測試)

在 PC 端開發時，系統會自動繞過實體 GPIO 與 SPI 呼叫，將狀態印出於終端機。

🔊 音訊硬體配置與測試 (Raspberry Pi)

本專案使用 I2S 介面實現全雙工語音互動，輸出採用 MAX98357A 音訊放大器，輸入採用 INMP441 數位麥克風。兩者共用樹莓派的時脈訊號引腳（BCLK / LRC），資料腳位（DIN / DOUT）則獨立分開。

1. 硬體接線對照表

訊號名稱

MAX98357A (喇叭)

INMP441 (麥克風)

Raspberry Pi 實體針腳 (Pin #)

說明

VCC

VIN (5V)

-

Pin 2 / 4

喇叭使用 5V 驅動音量較足

VDD

-

VDD (3.3V)

Pin 1 / 17

麥克風請務必接 3.3V

GND

GND

GND

GND 針腳

共同接地

LRC / WS

LRC

LCLK

Pin 35 (GPIO 19)

共線分接 (左右聲道時脈)

BCLK

BCLK

BCLK

Pin 12 (GPIO 18)

共線分接 (位元時脈)

DIN / DOUT

DIN

-

Pin 40 (GPIO 21)

音訊輸出 (RPi DOUT)

SD / DATA

-

SD

Pin 38 (GPIO 20)

音訊輸入 (RPi DIN)

L/R (設定)

-

L/R

接 GND
