Snowboard Agent
「精簡、幽默、帶點歪理。」—— 離線即時邊緣 AI 語音助理

Snowboard 是一個運行於邊緣設備（Raspberry Pi 5 4GB）上的全離線語音助理系統。她不僅具備自然、無延遲的語音對話能力（搭配 Anne Hathaway 聲線的中文發音），還結合了視覺辨識功能，並能透過 LED 與 1 吋 LCD 螢幕與外部世界進行即時的狀態互動。

本專案 (snowboard-agent) 為系統的中樞大腦，負責調度 ASR、LLM、TTS、視覺模型以及底層硬體驅動。

✨ 系統特色 (Key Features)
🧠 離線邊緣運算：所有認知模組（ASR 語音轉文字、本地 LLM 推理、TTS 語音生成）皆於本地端執行，確保隱私與極低延遲。

👁️ 視覺感知能力：整合攝影鏡頭，能即時辨識眼前物體並融入對話情境中。

🎭 靈魂與人格化：內建狀態機管理（聆聽、思考、回答），並擁有獨特的性格設定與專屬聲線。

💻 跨平台開發架構：支援 PC 與 RPi 雙環境。在 PC 開發時會自動模擬 (Mock) 實體硬體行為，確保 AI 模組測試與硬體佈署的無縫銜接。

📁 專案架構 (Directory Structure)
專案採用「軟硬解耦」的模組化設計：

Plaintext


snowboard-agent/
├── main.py              # 系統大腦入口：初始化模組、播放動畫並進入主狀態機迴圈
├── config/              # 系統設定檔 (GPIO 腳位、模型路徑、喚醒詞)
├── core/                # 認知中樞
│   ├── agent.py         # 狀態機管理 (Booting -> Idle -> Listening -> Thinking -> Speaking)
│   └── personality.py   # System Prompts (精簡、幽默、歪理邏輯)
├── ai/                  # AI 模型抽象層 (ASR, LLM, TTS, Vision)
├── hw/                  # 硬體驅動層 (LED, LCD, Audio, Camera)
├── tests/               # 獨立測試腳本 (單獨測試聽覺、大腦或發聲，免啟動主程式)
├── assets/              # 靜態資源 (LCD 開機動畫、系統提示音)
├── requirements-core.txt # 跨平台共用依賴 (PC & RPi)
└── requirements-rpi.txt  # RPi 專屬硬體驅動依賴
🚀 快速啟動 (Getting Started)
1. 開發環境設置 (PC 端測試)
在 PC 端開發時，系統會自動繞過實體 GPIO 與 SPI 呼叫，將狀態印出於終端機。

Bash


# 複製專案
git clone https://github.com/你的帳號/snowboard-agent.git
cd snowboard-agent

# 建立虛擬環境並啟動
python -m venv venv
source venv/bin/activate  # Windows 請使用 venv\Scripts\activate

# 安裝核心依賴
pip install -r requirements-core.txt

# 使用 PC 環境變數進行測試
ENV=PC python main.py
2. 實機佈署 (Raspberry Pi 5)
當準備將程式搬上實體機器時，請額外安裝硬體驅動依賴。

Bash


# 在 RPi 上安裝額外的硬體驅動 (如 RPi.GPIO, spidev)
pip install -r requirements-rpi.txt

# 啟動主程式 (將會驅動實體 LED 與 LCD)
ENV=RPI python main.py
🛠️ 模組獨立測試
為了加速開發，本專案支援各別 AI 模組的脫機測試。請進入 tests/ 目錄執行對應腳本：

測試聽覺 (ASR): python tests/test_asr.py (讀取預錄音檔測試辨識率)

測試大腦 (LLM): python tests/test_llm.py (終端機文字對話，測試幽默回覆邏輯)

測試發聲 (TTS): python tests/test_tts.py (生成語音並輸出至本機音效卡)

