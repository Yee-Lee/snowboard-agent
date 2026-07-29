import ctypes
import time
from PIL import Image

# 1. 載入動態連結庫
oled_lib = ctypes.CDLL('./libdisplay.so')

# 定義 C 函式簽名
oled_lib.init_display.argtypes = []
oled_lib.init_display.restype = None
oled_lib.push_frame.argtypes = [ctypes.c_char_p, ctypes.c_int]
oled_lib.push_frame.restype = None
oled_lib.close_display.argtypes = []
oled_lib.close_display.restype = None

# 初始化顯示器
oled_lib.init_display()

WIDTH, HEIGHT = 128, 128

# 建立靜態畫面顏色列表
colors = [
    ("全黑 (Black - 0%)", (0, 0, 0)),
    ("低灰 (Low Gray - 25%)", (64, 64, 64)),
    ("中灰 (Mid Gray - 50%)", (128, 128, 128)),
    ("高灰 (High Gray - 75%)", (192, 192, 192)),
    ("全白 (White - 100%)", (255, 255, 255)),
]

print("==========================================")
print(" 靜態畫面測試 (Static Frame Test)")
print(" 用途: 檢測電源波動 (Power ripple) 與控制器閃爍")
print(" 請使用手機 60 FPS 錄影觀察畫面是否穩定無水波紋/閃爍")
print(" 按 Ctrl+C 可隨時結束")
print("==========================================")

try:
    for name, rgb in colors:
        print(f"\n[目前顯示]: {name} RGB={rgb}")
        img = Image.new('RGB', (WIDTH, HEIGHT), color=rgb)
        raw_data = img.tobytes()
        
        # 刷新畫面 (發送幾次確保寫入成功)
        for _ in range(3):
            oled_lib.push_frame(raw_data, len(raw_data))
        
        print("展示 5 秒中...請觀察手機錄影畫面")
        time.sleep(5.0)

    print("\n所有靜態畫面測試完畢！")

finally:
    oled_lib.close_display()
    print("顯示器已關閉。")
