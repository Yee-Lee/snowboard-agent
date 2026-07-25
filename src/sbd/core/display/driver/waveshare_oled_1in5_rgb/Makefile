# Makefile for Waveshare 1.5-inch RGB OLED Driver

# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -fPIC -I.
LDFLAGS = -shared
LIBS = -llgpio

# Source files
SRCS = OLED_1in5_rgb.c DEV_Config.c display_driver.c
OBJS = $(SRCS:.c=.o)

# Target shared library
TARGET = libdisplay.so

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^ $(LIBS)

.c.o:
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)