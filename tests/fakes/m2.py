"""Deterministic M2 fixtures and race-control helpers.

These helpers intentionally depend only on the standard library. Product
objects are injected by each test so importing the fixture layer cannot load a
Pi-only backend or accidentally perform hardware/network I/O.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallLog:
    """Ordered call recorder with explicit ordering assertions."""

    entries: list[tuple[str, Any]] = field(default_factory=list)

    def record(self, name: str, value: Any = None) -> None:
        self.entries.append((name, value))

    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.entries)

    def assert_before(self, first: str, second: str) -> None:
        names = self.names()
        assert first in names, f"missing call: {first}"
        assert second in names, f"missing call: {second}"
        assert names.index(first) < names.index(second), (
            f"expected {first!r} before {second!r}, got {names!r}"
        )


class AsyncBarrier:
    """Pause one coroutine at a named linearization point without sleeps."""

    def __init__(self) -> None:
        self.arrived = asyncio.Event()
        self.released = asyncio.Event()
        self.point: str | None = None

    async def pause(self, point: str) -> None:
        assert self.point is None, "barrier supports one arrival per fixture"
        self.point = point
        self.arrived.set()
        await self.released.wait()

    async def wait_until_arrived(self) -> str:
        await self.arrived.wait()
        assert self.point is not None
        return self.point

    def release(self) -> None:
        assert self.arrived.is_set(), "cannot release before arrival"
        self.released.set()


@dataclass(frozen=True)
class MockHalFixture:
    """Small valid PCM/image/display samples for FX-MOCK-HAL."""

    sample_rate_hz: int = 16_000
    channels: int = 1
    sample_width_bytes: int = 2
    pcm_frame: bytes = b"\x00\x00" * 160
    image_width: int = 2
    image_height: int = 2
    blank_rgb: bytes = b"\x00" * 12


@dataclass(frozen=True)
class MockWorkerFixture:
    """Deterministic adapter outputs for FX-MOCK-WORKER."""

    asr_text: str = "fixture transcript"
    vision_text: str = "fixture scene"
    tts_pcm: bytes = b"\x01\x00" * 80
    llm_speak_json: str = '{"kind":"speak","payload":{"text":"fixture reply"}}'
    llm_rest_json: str = '{"kind":"rest","payload":{}}'


@dataclass(frozen=True)
class MessageFixture:
    """Stable arrival data for FX-MESSAGE."""

    texts: tuple[str, ...] = ("first message", "second message")
    metadata: tuple[tuple[str, str], ...] = (("source", "fixture"),)


@dataclass(frozen=True)
class MockAppFixture:
    """Expected mock-session inputs and state path for FX-MOCK-APP."""

    input_kinds: tuple[str, ...] = (
        "ButtonPressed",
        "WakeWordDetected",
        "ExternalMessageArrived",
    )
    state_path: tuple[str, ...] = (
        "IDLE",
        "WAKE",
        "PERCEPTION",
        "THINK",
        "ACTION",
        "IDLE",
    )
