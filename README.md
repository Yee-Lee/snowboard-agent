Snowboard Agent
「精簡、幽默、帶點歪理。」—— 離線即時邊緣語音助理

Linux driver


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


