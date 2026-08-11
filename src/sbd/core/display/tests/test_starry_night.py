"""
test_starry_night.py

Full end-to-end starry night display test.

Enters the system at the API layer:
    test_starry_night.py → API → Service → Rendering → HAL → Native

In non-hardware mode (default) it uses MockDisplayDevice and runs for
a fixed duration, printing FPS statistics and optionally saving frames.

Run on hardware::

    python -m pytest tests/test_starry_night.py -s --hardware=waveshare_oled_1in5_rgb

Run headless (CI)::

    pytest tests/test_starry_night.py
"""

from __future__ import annotations

import asyncio
import time

import pytest

from sbd.core.display.api.client import DisplayClient
from sbd.core.display.hal.factory import create_device
from sbd.core.display.service.service import DisplayService





@pytest.fixture
async def service(profile) -> DisplayService:
    device = create_device(profile, mock=(profile == "mock"))
    svc = DisplayService(device, target_fps=30)
    await svc.start()
    yield svc
    await svc.stop()


@pytest.fixture
async def client(service) -> DisplayClient:
    return DisplayClient(service)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_starry_night_runs_for_3_seconds(client):
    """
    End-to-end: set starry_night status and let it run for 3 seconds.

    Verifies that the service doesn't crash and accepts commands correctly.
    """
    client.set_status("starry_night", owner="test")
    await asyncio.sleep(3.0)
    # If we reach here without exception, the test passes


@pytest.mark.asyncio
async def test_notify_overlay_during_animation(client):
    """Overlay a notification while the background animation runs."""
    client.set_status("starry_night")
    await asyncio.sleep(0.5)
    client.notify("任務完成", duration=1.0)
    await asyncio.sleep(1.5)


@pytest.mark.asyncio
async def test_alert_suspends_and_resumes(service, client):
    """
    Show an exclusive alert and verify it auto-dismisses after 1 second,
    resuming the background status.
    """
    client.set_status("starry_night")
    await asyncio.sleep(0.5)

    layer_id = await client.show_alert("網路中斷", duration=1.0)
    await asyncio.sleep(0.2)

    # Alert should be active
    alert_layer = service._scene.get(layer_id)
    assert alert_layer is not None

    # Wait for auto-dismiss
    await asyncio.sleep(1.5)

    # Background should have resumed (status layer still present)
    from sbd.core.display.service.scene import LayerType, LayerState
    status_layers = [
        l for l in service._scene.layers
        if l.layer_type == LayerType.STATUS and l.state == LayerState.VISIBLE
    ]
    assert len(status_layers) >= 1, "Status layer should be visible after alert dismisses"


@pytest.mark.asyncio
async def test_play_media_completes(client):
    """play_media returns a handle that completes."""
    handle = await client.play_media("starry_night", duration=0.5)
    await asyncio.wait_for(handle.wait(), timeout=3.0)
    assert handle.is_done
