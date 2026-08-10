#!/usr/bin/env python3
import sys
import os
import time

# Add lib to Python path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_OLED import OLED_1in5_rgb
from PIL import Image, ImageDraw

def fast_show_image(disp, pBuf):
    """Chunked SPI write (like python_backend.py)"""
    disp.command(0x15)
    disp.data(0x00)
    disp.data(0x7f)
    disp.command(0x75)
    disp.data(0x00)
    disp.data(0x7f)
    disp.command(0x5C)
    
    disp.digital_write(disp.DC_PIN, True)
    
    chunk_size = 4096
    buf = memoryview(pBuf)
    for i in range(0, len(buf), chunk_size):
        chunk = buf[i:i+chunk_size].tolist()
        disp.spi.writebytes(chunk)

def main():
    print("Initializing OLED...")
    disp = OLED_1in5_rgb.OLED_1in5_rgb()
    if disp.Init() == -1:
        print("Init failed!")
        return
    disp.clear()

    print("Running animation test...")
    for i in range(30):
        # Create a blank black image
        image = Image.new('RGB', (disp.width, disp.height), "BLACK")
        draw = ImageDraw.Draw(image)
        
        # Draw a moving white square
        x = i * 3
        draw.rectangle([(x, 50), (x+20, 70)], fill="WHITE")
        
        # Convert PIL to RGB565 byte buffer using the official getbuffer
        buf = disp.getbuffer(image)
        
        # Use our optimized chunked write
        fast_show_image(disp, bytes(buf))
        
        print(f"Frame {i+1}/30 rendered")
        time.sleep(0.05)

    print("Done!")

if __name__ == '__main__':
    main()
