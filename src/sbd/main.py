"""Snowboard entry point.

M1 wires up the backbone only: config, logger, event bus, state manager.
Workers, adaptors and hardware drivers are attached in later milestones.
"""

from __future__ import annotations

import asyncio
import logging

from sbd.core.config import load_settings
from sbd.core.event_bus import EventBus
from sbd.core.logger import setup_logging
from sbd.core.state_manager import StateManager

log = logging.getLogger(__name__)


async def _run() -> None:
    settings = load_settings()
    setup_logging(settings)

    bus = EventBus()
    sm = StateManager(bus, settings.state_manager)

    log.info("Snowboard M1 backbone ready; state=%s", sm.state.value)
    await sm.wait_until_shutdown()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
