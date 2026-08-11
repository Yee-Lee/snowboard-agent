from __future__ import annotations
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--hardware",
        default=None,
        help="Panel profile to use for hardware tests (e.g. waveshare_oled_1in5_rgb)",
    )

@pytest.fixture
def profile(request) -> str:
    return request.config.getoption("--hardware") or "mock"
