"""M3 HAL factory and fallback tests."""

from __future__ import annotations

import asyncio
import sys

from sbd.core.audio import make_audio_input, make_audio_output
from sbd.core.camera import make_camera
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import AudioConfig, CameraConfig, DisplayConfig, GPIOConfig
from sbd.core.display import make_display
from sbd.core.event_bus import EventBus
from sbd.core.gpio import make_gpio
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase


class Resource:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.stop_calls = 0
    async def start(self):
        if self.fail:
            raise RuntimeError("fixture start failure")
    async def stop(self):
        self.stop_calls += 1


def _session_skeleton(rm):
    for key in (
        "worker.perception.listen", "worker.cognition.reasoner", "worker.action.rest"
    ):
        rm.register(ResourceSpec(key=key, phase=StartPhase.WORKER, factory=lambda _: Resource()))


def test_m3_hal_001() -> None:
    modules_before = set(sys.modules)
    for driver in ("null", "mock"):
        assert make_audio_input(AudioConfig(driver=driver)) is not None
        assert make_audio_output(AudioConfig(driver=driver)) is not None
        assert make_display(DisplayConfig(driver=driver)) is not None
        assert make_camera(CameraConfig(driver=driver)) is not None
    assert make_gpio(GPIOConfig(driver="mock")) is not None
    forbidden = {"alsaaudio", "sounddevice", "picamera2", "gpiod", "samplerate"}
    roots = {
        name.split(".", 1)[0]
        for name in set(sys.modules).difference(modules_before)
    }
    assert forbidden.isdisjoint(roots)
    assert not any(
        "ssd1351" in name
        for name in set(sys.modules).difference(modules_before)
    )


def test_m3_hal_002() -> None:
    async def scenario():
        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        for kind in ("audio", "display", "camera"):
            rm.register(ResourceSpec(
                key=f"core.{kind}", phase=StartPhase.CORE,
                factory=lambda _: Resource(fail=True),
                null_factory=lambda _: Resource(), capability_kind=kind,
            ))
        rm.register(ResourceSpec(
            key="core.gpio", phase=StartPhase.CORE,
            factory=lambda _: Resource(fail=True), required=False,
            capability_kind="gpio",
        ))
        _session_skeleton(rm)
        await rm.start()
        assert {kind: rm.capability_of(kind) for kind in ("audio", "display", "camera", "gpio")} == {
            "audio": False, "display": False, "camera": False, "gpio": False,
        }
        await rm.stop_all()

        fatal = ResourceManager(DEFAULT_CONFIG, EventBus())
        fatal.register(ResourceSpec(
            key="core.audio", phase=StartPhase.CORE,
            factory=lambda _: Resource(fail=True),
            null_factory=lambda _: Resource(fail=True), capability_kind="audio",
        ))
        _session_skeleton(fatal)
        try:
            await fatal.start()
        except Exception as exc:
            assert "fixture start failure" in str(exc) or exc.__cause__ is not None
        else:
            raise AssertionError("null fallback failure must abort startup")
    asyncio.run(scenario())
