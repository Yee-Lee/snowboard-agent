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

def main():
    print("Initializing OLED...")
    disp = OLED_1in5_rgb.OLED_1in5_rgb()
    if disp.Init() != 0:
        print("Initialization failed!")
        return

    print("Clearing display...")
    disp.clear()

    print("Drawing test pattern...")
    image = Image.new('RGB', (disp.width, disp.height), "BLACK")
    draw = ImageDraw.Draw(image)

    # Draw a red border
    draw.rectangle([(0, 0), (disp.width - 1, disp.height - 1)], outline="RED")
    
    # Draw some colored rectangles
    draw.rectangle([(20, 20), (50, 50)], fill="BLUE")
    draw.rectangle([(60, 20), (90, 50)], fill="GREEN")
    
    print("Sending image to display...")
    disp.ShowImage(disp.getbuffer(image))
    print("Done! Look at the OLED screen.")

if __name__ == '__main__':
    main()
