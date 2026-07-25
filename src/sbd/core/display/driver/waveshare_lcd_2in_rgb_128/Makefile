# Makefile for Waveshare 2-inch LCD Driver

# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -fPIC -I. -DUSE_DEV_LIB=1
LDFLAGS = -shared
LIBS = -llgpio

# Source files
SRCS = LCD_2inch.c DEV_Config.c display_driver.c
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