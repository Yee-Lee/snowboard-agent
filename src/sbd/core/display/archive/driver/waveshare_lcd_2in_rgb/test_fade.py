import ctypes
import time
import os
from PIL import Image, ImageDraw

# 1. 載入動態連結庫
dir_path = os.path.dirname(os.path.realpath(__file__))
so_path = os.path.join(dir_path, 'libdisplay.so')
oled_lib = ctypes.CDLL(so_path)
oled_lib.init_display()

WIDTH, HEIGHT = 320, 240

# 2. 準備兩張畫布：一張純黑，一張目標照片
black_img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))

# 嘗試載入同一資料夾下的 'photo.jpg'
PHOTO_PATH = 'photo.jpg'
if os.path.exists(PHOTO_PATH):
    print(f"找到照片 {PHOTO_PATH}，正在裁切調整大小...")
    target_img = Image.open(PHOTO_PATH).convert('RGB')
    # 使用 LANCZOS 高品質縮放，並置中裁切成 320x240
    from PIL import ImageOps
    target_img = ImageOps.fit(target_img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
else:
    print(f"找不到 {PHOTO_PATH}，產生預設的高飽和度霓虹漸層測試圖...")
    target_img = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(target_img)
    # 畫一個色彩鮮豔的測試圖案，用來測試色彩飽和度
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r = int((x / WIDTH) * 255)
            b = int((y / HEIGHT) * 255)
            draw.point((x, y), fill=(r, 50, b))
    # 正中央加一個極亮的光球 (在 320x240 橫向螢幕上居中)
    draw.ellipse([100, 60, 220, 180], fill=(255, 200, 50))

print("啟動漸顯漸隱測試... (按 Ctrl+C 結束)")

# 3. 定義 10 秒一個循環的時間軸劇本
def get_alpha(t):
    """計算透明度 (0.0=純黑, 1.0=全圖)"""
    cycle = t % 10.0
    if cycle < 3.0:
        # 階段 1：淡入 (0.0 -> 1.0)，耗時 3 秒
        return cycle / 3.0
    elif cycle < 5.0:
        # 階段 2：全亮展示，維持 2 秒
        return 1.0
    elif cycle < 8.0:
        # 階段 3：淡出 (1.0 -> 0.0)，耗時 3 秒
        return 1.0 - ((cycle - 5.0) / 3.0)
    else:
        # 階段 4：純黑展示，維持 2 秒 (OLED 消失的瞬間)
        return 0.0

anim_start_time = time.time()
TARGET_FPS = 60
FRAME_TIME = 1.0 / TARGET_FPS

try:
    while True:
        loop_start = time.time()
        current_time = time.time() - anim_start_time
        
        # 取得當前的透明度
        alpha = get_alpha(current_time)
        
        # 使用 PIL 內建的 blend 進行影像混合 (底圖, 上層圖, 透明度)
        blend_img = Image.blend(black_img, target_img, alpha)

        # 轉換並送給 C 驅動
        raw_data = blend_img.tobytes() 
        oled_lib.push_frame(raw_data, len(raw_data))
        
        # 穩定更新率
        work_time = time.time() - loop_start
        if work_time < FRAME_TIME:
            time.sleep(FRAME_TIME - work_time)

except KeyboardInterrupt:
    oled_lib.close_display()
    print("動畫結束")
