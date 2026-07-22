# ==========================================
# Compiler Settings
# ==========================================
CC = gcc

# 參數說明：
# -fPIC : 產生位置無關代碼 (Shared Library 必備)
# -O3   : 最高階最佳化 (極大化 C 迴圈壓縮 Framebuffer 的效能)
# -Wall : 顯示所有編譯警告
# -I./  : 讓編譯器在當前目錄尋找 .h 標頭檔

# 加上 -DUSE_DEV_LIB 強制啟用 lgpio 分支
CFLAGS = -fPIC -O3 -Wall -I./ -DUSE_DEV_LIB

# 連結參數：
# -shared : 告訴 gcc 要輸出 .so 動態連結庫
# -lgpiod : 連結 Raspberry Pi 5 的 GPIO 函式庫 
# (註：若你的 DEV_Config.c 依賴其他函式庫如 -llgpio 或 -lbcm2835，請在這裡替換)

# 改為連結 lgpio 與 math 庫
LDFLAGS = -shared -llgpio -lm


# ==========================================
# Files and Targets
# ==========================================
# 輸出的動態連結庫名稱
TARGET = libdisplay.so

# 參與編譯的原始碼檔案
SRCS = display_driver.c OLED_1in5_rgb.c DEV_Config.c

# 自動將 .c 替換成 .o，產生對應的 Object Files 列表
OBJS = $(SRCS:.c=.o)

# ==========================================
# Build Rules
# ==========================================
# 預設目標
all: $(TARGET)

# 連結 .o 檔成為 .so 動態連結庫
$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^
	@echo "編譯完成！已產生 $(TARGET)"

# 編譯每一個 .c 檔成為 .o 檔
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 清除編譯產生的暫存檔與目標檔
clean:
	rm -f $(OBJS) $(TARGET)
	@echo "清理完成！"

# 宣告偽目標 (避免目錄下剛好有叫做 all 或 clean 的檔案導致衝突)
.PHONY: all clean
