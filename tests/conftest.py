"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from sbd.core.config import StateManagerSettings
from sbd.core.event_bus import EventBus
from sbd.core.state_manager import StateManager


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def sm_settings() -> StateManagerSettings:
    return StateManagerSettings(
        error_recovery_seconds=0.0,
        perception_timeout_seconds=1.0,
    )


@pytest.fixture
def sm(bus: EventBus, sm_settings: StateManagerSettings) -> StateManager:
    return StateManager(bus, sm_settings)
