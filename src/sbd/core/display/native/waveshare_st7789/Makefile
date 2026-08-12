# Makefile for waveshare_st7789 native driver
# Produces libdisplay.so implementing the stable C ABI in native/include/display.h

CC      := gcc
CFLAGS  := -O2 -Wall -Wextra -fPIC -I../include -pthread
LDFLAGS := -shared -Wl,-z,defs
LDLIBS  := -llgpio -pthread

SRCS := display_driver.c ../dev_config_runtime.c LCD_2inch.c
OBJS := $(SRCS:.c=.o)
TARGET := libdisplay.so

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^ $(LDLIBS)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET)
