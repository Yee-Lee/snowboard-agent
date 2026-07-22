import ctypes
import time
import random
from PIL import Image, ImageDraw

# 1. 載入動態連結庫
oled_lib = ctypes.CDLL('./libdisplay.so')
oled_lib.init_display()

WIDTH, HEIGHT = 128, 128
img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# 2. 定義 3D 星星類別 (不需要紀錄軌跡了)
class Star:
    def __init__(self):
        self.x = random.uniform(-1, 1)
        self.y = random.uniform(-1, 1)
        self.z = random.uniform(0.1, 2.0)
        self.base_speed = random.uniform(0.01, 0.03)

    def reset(self):
        self.x = random.uniform(-1, 1)
        self.y = random.uniform(-1, 1)
        self.z = 2.0
        self.base_speed = random.uniform(0.01, 0.03)

    def update(self, warp_factor):
        # 套用全域加速倍率
        self.z -= self.base_speed * warp_factor
        
        if self.z <= 0.01:
            self.reset()

stars = [Star() for _ in range(150)]

print("啟動流星點點... (按 Ctrl+C 結束)")

frame_count = 0
fps_start_time = time.time()
anim_start_time = time.time()
TARGET_FPS = 120
FRAME_TIME = 1.0 / TARGET_FPS

def get_warp_factor(t):
    """計算加速倍率，8 秒循環 (1 倍速 ~ 4.5 倍速)"""
    cycle = t % 8.0
    if cycle < 2.0:
        return 1.0       # 階段 1：悠哉巡航 (1.0 倍速)
    elif cycle < 4.0:
        # 階段 2：飆速加速 (2 秒)
        progress = (cycle - 2.0) / 2.0
        return 1.0 + (progress ** 3) * 3.5 
    elif cycle < 4.5:
        # 階段 3：極速狀態 (維持 4.5 倍速)
        return 4.5      
    else:
        # 階段 4：漫長減速 (3.5 秒)
        progress = (cycle - 4.5) / 3.5
        return 4.5 - (progress ** 1.5) * 3.5

try:
    while True:
        loop_start = time.time()
        current_time = time.time() - anim_start_time
        
        # 取得當前時間點的「加速倍率」
        warp_factor = get_warp_factor(current_time)
        
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(0, 0, 0))
        
        for star in stars:
            star.update(warp_factor)
            
            # 投影當前座標
            sx = int((star.x / star.z) * (WIDTH / 2) + (WIDTH / 2))
            sy = int((star.y / star.z) * (HEIGHT / 2) + (HEIGHT / 2))
            
            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                # 距離越近越亮 (0~255)
                brightness = int((1 - (star.z / 2.0)) * 255)
                r = int(brightness * 0.5)
                g = int(brightness * 0.9)
                b = brightness
                
                # 移除畫線邏輯，一律只畫點 (靠近時稍微變大，增加立體感)
                size = 2 if star.z < 0.4 else 1
                draw.rectangle([sx, sy, sx+size, sy+size], fill=(r, g, b))

        raw_data = img.tobytes() 
        oled_lib.push_frame(raw_data, len(raw_data))
        
        # 效能與狀態監控
        frame_count += 1
        elapsed = time.time() - fps_start_time
        if elapsed >= 1.0:
            print(f"效能: {frame_count} FPS | 當前曲速: {warp_factor:.1f}x")
            frame_count = 0
            fps_start_time = time.time()
            
        work_time = time.time() - loop_start
        if work_time < FRAME_TIME:
            time.sleep(FRAME_TIME - work_time)

except KeyboardInterrupt:
    oled_lib.close_display()
    print("動畫結束")
