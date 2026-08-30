#!/usr/bin/env python3
"""
Snowboard Manual Button Tester

A dedicated utility script to manually verify the physical GPIO button wiring.
It will wait indefinitely for a physical button press to confirm the circuit.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import asyncio
import logging

from sbd.core.config import load_config
from sbd.core.gpio.gpiod.driver import GpiodGPIO

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("button_test")

async def main():
    logger.info("Loading configuration...")
    config_path = Path("config.local.yaml") if Path("config.local.yaml").exists() else (Path("config.m3.local.yaml") if Path("config.m3.local.yaml").exists() else Path("config.local.yaml"))
    config = load_config(local_path=config_path)
    
    try:
        gpio = GpiodGPIO(config.core.gpio)
        await gpio.start()
        
        pressed = asyncio.Event()
        
        async def on_button_press(event):
            logger.info(f"\n🎉 SUCCESS: Physical button press detected on Pin {event.pin}! (Edge: {event.edge})")
            pressed.set()
            
        pin = 23 
        if "conversation" in config.core.gpio.pins:
            pin = config.core.gpio.pins["conversation"].pin
            
        await gpio.register_input(pin, "falling", on_button_press, debounce_ms=50)
        
        logger.info(f"✅ GPIO driver bound successfully for Pin {pin}.")
        logger.info("👉 Please press the physical button now... (Press Ctrl+C to exit)")
        
        # Wait indefinitely until the button is pressed
        await pressed.wait()
            
        await gpio.unregister(pin)
        await gpio.stop()
    except Exception as e:
        logger.error(f"❌ GPIO test failed: {e}\n", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nTest cancelled by user.")
