import ctypes
import time
import os
from PIL import Image, ImageDraw, ImageFont

# 1. 載入動態連結庫
dir_path = os.path.dirname(os.path.realpath(__file__))
so_path = os.path.join(dir_path, 'libdisplay.so')
oled_lib = ctypes.CDLL(so_path)
oled_lib.init_display()

WIDTH, HEIGHT = 128, 128

# 2. 載入繁體中文字體 (字體縮小至 12)
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 12)
except IOError:
    print("找不到字體檔！請確認是否已執行 sudo apt-get install fonts-wqy-microhei")
    exit()

# 3. 定義角色與專屬顏色 (RGB)，中英文角色共用顏色設定
COLORS = {
    "系統": (120, 120, 120),     # 系統提示：低調暗灰
    "Ned": (255, 200, 50),       # 奈德 (英)：驚訝的亮黃色
    "Peter": (255, 80, 80),      # 彼得 (英)：蜘蛛人紅
    "奈德": (255, 200, 50),      # 奈德 (中)
    "彼得": (255, 80, 80)        # 彼得 (中)
}

# 4. 雙語對白劇本：先英文，再由系統接入中文翻譯
raw_script = [
    ("系統", "[System] Intercepting unauthorized audio..."),
    ("Ned", "You're the Spider-Man... from YouTube!"),
    ("Peter", "No, no, no! I'm not! It's just a costume!"),
    ("Ned", "You were on the ceiling!"),
    ("Peter", "I was... cleaning! Please don't tell anyone!"),
    ("系統", "----------------"),
    ("系統", "[系統] 啟動即時神經翻譯模組..."),
    ("奈德", "你是蜘蛛人……YouTube 上那個！"),
    ("彼得", "不不不！我不是！這只是一件變裝服！"),
    ("奈德", "你剛剛爬在天花板上耶！"),
    ("彼得", "我剛剛是在……打掃！求你千萬別告訴任何人！"),
    ("系統", "================")
]

# 5. 自動測量寬度與斷行處理
def wrap_text(script, font, max_width):
    wrapped_lines = []
    for speaker, text in script:
        # 系統訊息不加前綴，人物訊息自動加上「名字: 」
        full_text = text if speaker == "系統" else f"{speaker}: {text}"
        
        current_line = ""
        for char in full_text:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line = test_line
            else:
                wrapped_lines.append((current_line, False, speaker))
                current_line = char 
                
        if current_line:
            wrapped_lines.append((current_line, True, speaker))
    return wrapped_lines

# 左右各預留 5 像素邊距 (配合 128 像素寬度)
messages = wrap_text(raw_script, font, 118)

print("啟動雙語劇本與平滑捲動測試... (按 Ctrl+C 結束)")

target_scroll_y = 0.0
current_scroll_y = 0.0
message_history = []
current_msg_idx = 0
typed_chars = 0
typing_speed = 28.0  # 稍微調快一點點以應付雙語的長度
line_height = 14     

last_time = time.time()
type_timer = 0.0
pause_timer = 0.0

try:
    while True:
        loop_start = time.time()
        dt = loop_start - last_time
        last_time = loop_start

        img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        # ==========================================
        # 邏輯更新
        # ==========================================
        if pause_timer > 0:
            pause_timer -= dt
        else:
            if current_msg_idx < len(messages):
                current_line_text, is_end_of_msg, speaker = messages[current_msg_idx]
                
                type_timer += dt
                if type_timer > (1.0 / typing_speed):
                    type_timer = 0.0
                    typed_chars += 1
                    
                    if typed_chars > len(current_line_text):
                        message_history.append((current_line_text, COLORS[speaker]))
                        current_msg_idx += 1
                        typed_chars = 0
                        
                        total_height = (len(message_history) + 1) * line_height
                        if total_height > HEIGHT - 5: 
                            target_scroll_y += line_height 
                        
                        if current_msg_idx == len(messages):
                            pause_timer = 4.0  # 劇本結束，停頓 4 秒
                        elif is_end_of_msg:
                            # 句尾停頓，英文節奏快一點點
                            pause_timer = 0.3  
                        else:
                            pause_timer = 0.0  
            else:
                current_msg_idx = 0
                message_history.clear()
                target_scroll_y = 0.0
                current_scroll_y = 0.0
                typed_chars = 0

        # ==========================================
        # 數學運算：平滑捲動
        # ==========================================
        current_scroll_y += (target_scroll_y - current_scroll_y) * 10.0 * dt

        # ==========================================
        # 渲染畫面
        # ==========================================
        y_pos = 5 - current_scroll_y 
        
        for msg_text, msg_color in message_history:
            if -line_height < y_pos < HEIGHT: 
                draw.text((5, int(y_pos)), msg_text, font=font, fill=msg_color)
            y_pos += line_height

        if current_msg_idx < len(messages):
            current_line_text, _, speaker = messages[current_msg_idx]
            current_text = current_line_text[:typed_chars]
            
            if int(time.time() * 4) % 2 == 0:
                current_text += "_"
            
            if -line_height < y_pos < HEIGHT:
                draw.text((5, int(y_pos)), current_text, font=font, fill=COLORS[speaker])

        raw_data = img.tobytes()
        oled_lib.push_frame(raw_data, len(raw_data))
        
        work_time = time.time() - loop_start
        if work_time < (1.0 / 60.0):
            time.sleep((1.0 / 60.0) - work_time)

except KeyboardInterrupt:
    oled_lib.close_display()
    print("動畫結束")
