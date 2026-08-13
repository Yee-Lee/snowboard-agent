"""M3 Boot/Shutdown Blank lifecycle ownership."""

from __future__ import annotations

import asyncio

from sbd.core.config.models import DisplayConfig
from sbd.core.display import DisplayArbiter, DisplayHint, RenderModel
from sbd.core.display.lifecycle import DisplayLifecycle
from sbd.core.display.mock import MockDisplay
from sbd.core.display.null import NullDisplay


class Renderer:
    def validate(self, hint): pass
    def render(self, *, size, model): return bytes(size[0] * size[1] * 2)


def test_m3_scn_001() -> None:
    async def run(device):
        arbiter = DisplayArbiter(device, Renderer())
        await arbiter.start()
        lifecycle = DisplayLifecycle(arbiter)
        assert lifecycle.begin_boot()
        arbiter.write_main(DisplayHint("main.text", {"text": "latest"}))
        lifecycle.finish_boot()
        assert arbiter.snapshot().fullscreen is None
        assert arbiter.snapshot().main.data["text"] == "latest"
        assert lifecycle.begin_shutdown()
        assert arbiter.snapshot().fullscreen.template == "fullscreen.blank"
        await arbiter.stop()
    asyncio.run(run(MockDisplay(DisplayConfig())))
    asyncio.run(run(NullDisplay()))
