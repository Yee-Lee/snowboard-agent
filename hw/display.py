import os
import time
import unicodedata

# 判斷目前執行環境，預設為 PC (Ubuntu 模擬)
ENV = os.getenv("ENV", "PC")

def get_display_width(text):
    """計算字串在終端機的實際顯示寬度（全形=2，半形=1）"""
    width = 0
    for char in text:
        # W: 寬字元, F: 全形字元, A: 模糊字元 (在中文終端機通常佔 2 格)
        if unicodedata.east_asian_width(char) in ('W', 'F', 'A'):
            width += 2
        else:
            width += 1
    return width

def init_display():
    """初始化顯示器"""
    if ENV == "RPI":
        # 未來這裡放真實的 SPI/I2C LCD 初始化邏輯
        print("[硬體] 初始化實體 SPI 顯示器...")
    else:
        print("[模擬] 🖥️ 虛擬顯示器已就緒...")

def show_text(text: str):
    """在螢幕上顯示文字"""
    if ENV == "RPI":
        # 未來這裡使用 PIL (Pillow) 繪製文字並推送到實體螢幕
        pass
    else:
        # 框內預設寬度為 22
        box_width = 22
        text_width = get_display_width(text)
        
        # 計算需要補足的空白數量
        padding = " " * max(0, box_width - text_width)
        
        print(f"\n[LCD 顯示] ┌────────────────────────┐")
        # 手動加上計算好的空白，確保右側對齊
        print(f"[LCD 顯示] │ {text}{padding} │")
        print(f"[LCD 顯示] └────────────────────────┘\n")

def play_startup_animation():
    """播放開機啟動動畫"""
    if ENV == "RPI":
        # 未來這裡放實體 LCD 的 GIF 或圖片輪播
        pass
    else:
        # --- 動態生成動畫陣列 ---
        track_length = 7   # 軌道的最大空白數量（決定動畫寬度）
        box_char = "◼︎"      # 跑動的方塊字元
        
        # 利用公式：左邊 i 個空白，右邊 (track_length - i) 個空白
        # range(track_length + 1) 會產生 0 ~ 7 的數字，共 8 個 frame
        wave_frames = [
            f"[ LCD ] {' ' * i}{box_char}{' ' * (track_length - i)}"
            for i in range(track_length + 1)
        ]
        # ------------------------

        for _ in range(1):
            for frame in wave_frames:
                print(f"\r{frame}", end="", flush=True)
                # 這裡把延遲調小一點 (0.1秒)，讓波浪看起來有高頻閃動的科技感
                time.sleep(0.1) 
                
        print() # 動畫結束後換行
