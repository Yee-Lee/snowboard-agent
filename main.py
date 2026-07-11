import os
import time
from hw import display

def main():
    env = os.getenv("ENV", "PC")
    print(f"=== 啟動 Snowboard Agent (環境: {env}) ===")

    # 1. 初始化硬體 (螢幕、LED等)
    display.init_display()

    # 2. 播放啟動動畫 (這個時間差未來會用來在背景載入 LLM 與 ASR 模型)
    print("\n系統日誌：開始載入 AI 認知模組...")
    display.play_startup_animation()
    
    # 模擬模型載入完成
    time.sleep(0.2) 

    # 3. 系統準備就緒，進入待機
    display.show_text("(¬_¬) 醒了。找我幹嘛？")
    print("系統日誌：Agent 已進入 Idle 狀態，等待喚醒... (按 Ctrl+C 關閉)")

    # 4. 進入主迴圈 (Event Loop)
    try:
        while True:
            # 目前先單純用 sleep 保持程式運行
            # 未來這裡會接手 core.agent 的狀態機，負責監聽麥克風
            time.sleep(1)
    except KeyboardInterrupt:
        # 優雅地關閉系統
        print("\n\n系統日誌：收到中斷訊號，正在關閉系統...")
        display.show_text("Zzz... 睡覺去。")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
