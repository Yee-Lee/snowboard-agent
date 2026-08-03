import argparse
import asyncio
import logging
import sys

# Import custom animators so they register themselves
import animators

from sbd.core.display.hal.factory import create_device
from sbd.core.display.service.service import DisplayService
from sbd.core.display.api.client import DisplayClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_runner")

async def main():
    parser = argparse.ArgumentParser(description="Display Architecture Demo Runner")
    parser.add_argument(
        "-p", "--profile", 
        type=str, 
        default="mock",
        choices=["mock", "oled_1.5", "lcd_2", "lcd_128"],
        help="The display profile to use (short name)."
    )
    parser.add_argument(
        "-s", "--scenario",
        type=str,
        default="starring",
        choices=["starring", "fade", "chat", "video"],
        help="The demo scenario to run."
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Target FPS for the display service (default: 30)."
    )
    args = parser.parse_args()

    # Map short names to actual HAL profile names
    PROFILE_MAP = {
        "mock": "mock",
        "oled_1.5": "waveshare_oled_1in5_rgb",
        "lcd_2": "waveshare_lcd_2in_rgb",
        "lcd_128": "waveshare_lcd_2in_rgb_128"
    }
    actual_profile = PROFILE_MAP[args.profile]

    logger.info(f"Starting demo with profile: {actual_profile}, scenario: {args.scenario}, target FPS: {args.fps}")

    # 1. Create Device & Service
    try:
        device = create_device(actual_profile)
    except Exception as e:
        logger.error(f"Failed to create device: {e}")
        sys.exit(1)

    service = DisplayService(device, target_fps=args.fps)
    
    # 2. Start Service
    await service.start()
    
    # 3. Create API Client
    client = DisplayClient(service)

    try:
        # 4. Execute Scenario
        if args.scenario == "starring":
            logger.info("Running Starring (Starry Night) Demo...")
            client.set_status("starry_night")
            # Run for 15 seconds
            await asyncio.sleep(15)
            
        elif args.scenario == "fade":
            logger.info("Running Fade Transition Demo...")
            client.set_status("fade_demo")
            # Run for 15 seconds (about 4 fade cycles)
            await asyncio.sleep(15)
            
        elif args.scenario == "chat":
            logger.info("Running Chat Demo...")
            # We use play_media so it acts as an overlay/exclusive layer, or just set_status
            client.set_status("chat_demo")
            # Wait enough time for chat to type out
            await asyncio.sleep(15)
            
        elif args.scenario == "video":
            logger.info("Running Video Playback Demo...")
            # Use play_media so it's a media layer
            handle = await client.play_media("video_demo")
            # Wait for some time since video animators loop indefinitely for this demo
            await asyncio.sleep(15)
            
        logger.info("Demo finished successfully.")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user.")
    finally:
        # 5. Stop Service gracefully
        await service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
