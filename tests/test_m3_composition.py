"""Portable M3 composition and capability regression."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import DisplayConfig
from sbd.core.event_bus import EventBus
from sbd.core.m3_composition import M3Composition
from sbd.core.resource_manager import ResourceManager


def test_m3_composition_display_chain_and_null_capability() -> None:
    async def run(config, expected):
        bus = EventBus()
        rm = ResourceManager(config, bus)
        composition = M3Composition()
        composition(rm, bus, config)
        await rm.start()
        assert rm.capability_of("display") is expected
        assert rm.capability_of("audio") is True
        report = await rm.stop_all()
        assert report.failures == ()

    asyncio.run(run(DEFAULT_CONFIG, True))
    null_core = replace(
        DEFAULT_CONFIG.core,
        display=DisplayConfig(driver="null"),
    )
    asyncio.run(run(replace(DEFAULT_CONFIG, core=null_core), False))
