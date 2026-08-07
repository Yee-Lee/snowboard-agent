"""Pytest configuration and shared fixtures for Snowboard tests."""

import pytest

from tests.fakes.m2 import (
    AsyncBarrier,
    CallLog,
    MessageFixture,
    MockAppFixture,
    MockHalFixture,
    MockWorkerFixture,
)


@pytest.fixture
def fx_barrier_worker() -> AsyncBarrier:
    """FX-BARRIER-WORKER: deterministic async linearization barrier."""
    return AsyncBarrier()


@pytest.fixture
def fx_call_log() -> CallLog:
    """Shared ordered call recorder for race and lifecycle evidence."""
    return CallLog()


@pytest.fixture
def fx_mock_hal() -> MockHalFixture:
    """FX-MOCK-HAL deterministic media samples."""
    return MockHalFixture()


@pytest.fixture
def fx_mock_worker() -> MockWorkerFixture:
    """FX-MOCK-WORKER deterministic adapter outputs."""
    return MockWorkerFixture()


@pytest.fixture
def fx_message() -> MessageFixture:
    """FX-MESSAGE stable arrival sequence and metadata."""
    return MessageFixture()


@pytest.fixture
def fx_mock_app() -> MockAppFixture:
    """FX-MOCK-APP stable input kinds and expected state path."""
    return MockAppFixture()

def pytest_collection_modifyitems(config, items):
    """Skip rpi-marked tests unless explicitly selected."""
    if config.getoption("-m", default=None):
        return
    skip_rpi = pytest.mark.skip(reason="needs Raspberry Pi 5 hardware, use -m rpi to run")
    for item in items:
        if "rpi" in item.keywords:
            item.add_marker(skip_rpi)
