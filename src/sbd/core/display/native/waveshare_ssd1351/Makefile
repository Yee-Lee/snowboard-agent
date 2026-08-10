# Makefile for waveshare_ssd1351 native driver
# Produces libdisplay.so implementing the stable C ABI in native/include/display.h

CC      := gcc
CFLAGS  := -O2 -Wall -fPIC -I../include
LDFLAGS := -shared -llgpio

SRCS := display_driver.c ../dev_config_runtime.c OLED_1in5_rgb.c
OBJS := $(SRCS:.c=.o)
TARGET := libdisplay.so

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET)
