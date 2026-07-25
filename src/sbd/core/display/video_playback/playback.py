
import ctypes
import subprocess
import time
import os

import ctypes
import subprocess
import time
import os
import argparse

# --- 配置 ---
DRIVER_CONFIG = {
    'waveshare_lcd_2in_rgb': {'width': 320, 'height': 240},
    'waveshare_lcd_2in_rgb_128': {'width': 128, 'height': 128},
    'waveshare_oled_1in5_rgb': {'width': 128, 'height': 128},
}
DEFAULT_DRIVER = 'waveshare_lcd_2in_rgb_128'
FPS = 24
VIDEO_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'countdown.mp4')

def get_args():
    parser = argparse.ArgumentParser(description='在 Waveshare 螢幕上播放影片')
    parser.add_argument(
        '--driver',
        type=str,
        default=DEFAULT_DRIVER,
        choices=DRIVER_CONFIG.keys(),
        help=f"選擇要使用的顯示驅動。預設: {DEFAULT_DRIVER}"
    )
    return parser.parse_args()

def main():
    args = get_args()
    driver_name = args.driver
    config = DRIVER_CONFIG[driver_name]
    WIDTH, HEIGHT = config['width'], config['height']

    print(f"使用驅動: {driver_name} ({WIDTH}x{HEIGHT})")

    # --- 載入顯示驅動 ---
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        so_path = os.path.join(dir_path, f'../driver/{driver_name}/libdisplay.so')
        display_lib = ctypes.CDLL(so_path)
    except OSError as e:
        print(f"錯誤: 無法載入顯示函式庫 {so_path}")
        print(f"請先在 'driver/{driver_name}' 目錄下執行 'make' 編譯驅動程式。")
        print(f"詳細錯誤: {e}")
        return

    # --- FFmpeg 指令 ---
    command = [
        'ffmpeg',
        '-i', VIDEO_PATH,
        '-f', 'image2pipe',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'rgb24',
        '-s', f'{WIDTH}x{HEIGHT}',
        '-'
    ]

    print("初始化顯示器...")
    display_lib.init_display()

    print(f"準備播放影片: {VIDEO_PATH}")
    print("啟動 FFmpeg 子程序...")
    
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_size = WIDTH * HEIGHT * 3
    frame_duration = 1.0 / FPS

    try:
        print("開始播放... (按 Ctrl+C 結束)")
        while True:
            start_time = time.time()

            raw_frame = pipe.stdout.read(frame_size)

            if not raw_frame or len(raw_frame) != frame_size:
                print("影片播放完畢。")
                break

            display_lib.push_frame(raw_frame, frame_size)
            
            elapsed = time.time() - start_time
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n偵測到使用者中斷。")
    finally:
        print("關閉顯示器與子程序...")
        display_lib.close_display()
        pipe.terminate()
        pipe.stdout.close()
        pipe.stderr.close()
        print("清理完成。")

if __name__ == '__main__':
    if not os.path.exists(VIDEO_PATH):
        print(f"錯誤: 找不到影片檔案 {VIDEO_PATH}")
    else:
        # 在 main 函式內部進行 so 檔案的檢查
        main()
