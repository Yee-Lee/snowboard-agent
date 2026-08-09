import unittest
import asyncio
import sys
from pathlib import Path

# Setup path to import sbd
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from sbd.core.display.hal.factory import create_device
from sbd.core.display.hal.protocol import DisplayDevice

class TestMockSmoke(unittest.TestCase):
    def test_mock_smoke_lifecycle(self):
        # Create a mock device
        device: DisplayDevice = create_device("mock", mock=True)
        
        # Test size
        w, h = device.size()
        self.assertEqual(w, 128)
        self.assertEqual(h, 128)
        
        # Test start
        asyncio.run(device.start())
        
        # Test clear
        device.clear()
        
        # Test write_pixels with correct size
        frame = bytes([0xFF, 0x00] * (w * h))
        device.write_pixels(frame)
        
        # Test show
        device.show()
        
        # Test stop
        asyncio.run(device.stop())
        asyncio.run(device.stop())

if __name__ == '__main__':
    unittest.main()
