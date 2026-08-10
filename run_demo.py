import asyncio
from sbd.core.display.hal.factory import create_device
from sbd.core.display.service.service import DisplayService
from sbd.core.display.api.client import DisplayClient

async def main():
    # 建立設備與服務
    device = create_device("waveshare_oled_1in5_rgb", mock=False)
    svc = DisplayService(device, target_fps=30)
    await svc.start()
    
    # 透過 Client 送出指令
    client = DisplayClient(svc)
    print("顯示星空動畫...")
    client.set_status("starry_night", owner="test")
    
    await asyncio.sleep(5.0)
    print("關閉顯示器...")
    await svc.stop()

if __name__ == "__main__":
    asyncio.run(main())
