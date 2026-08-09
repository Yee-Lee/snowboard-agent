"""Small stdlib-only smoke for the compatibility POC service."""

import asyncio

from sbd.core.display.hal.factory import create_device
from sbd.core.display.service.service import DisplayService


async def main() -> None:
    device = create_device("mock", mock=True)
    service = DisplayService(device, target_fps=10)
    await service.start()
    await service.set_status("starry_night")
    await asyncio.sleep(0.2)
    await service.stop()
    print("service lifecycle smoke: OK")


if __name__ == "__main__":
    asyncio.run(main())
