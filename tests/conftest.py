"""Pytest configuration and shared fixtures for Snowboard tests."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip rpi-marked tests unless explicitly selected."""
    if config.getoption("-m", default=None):
        return
    skip_rpi = pytest.mark.skip(reason="needs Raspberry Pi 5 hardware, use -m rpi to run")
    for item in items:
        if "rpi" in item.keywords:
            item.add_marker(skip_rpi)
