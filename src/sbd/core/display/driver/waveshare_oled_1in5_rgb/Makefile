# ==========================================
# Compiler Settings
# ==========================================
CC = gcc
CFLAGS = -fPIC -O3 -Wall -I./ -DUSE_DEV_LIB
# 把 -shared 移到下方編譯指令，這裡保留需要連結的庫
LIBS = -llgpio -lm

# ==========================================
# Files and Targets
# ==========================================
TARGET = libdisplay.so
SRCS = display_driver.c OLED_1in5_rgb.c DEV_Config.c
OBJS = $(SRCS:.c=.o)

# ==========================================
# Build Rules
# ==========================================
all: $(TARGET)

# 注意這裡：$^ (代表所有的 .o 檔) 必須放在 $(LIBS) 前面
$(TARGET): $(OBJS)
	$(CC) -shared -o $@ $^ $(LIBS)
	@echo "編譯完成！已產生 $(TARGET)"

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
	@echo "清理完成！"

.PHONY: all clean
