import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--display-config",
        action="store",
        default=None,
        help="Path to the recorded local display fixture config JSON",
    )

@pytest.fixture
def display_config_path(request):
    path = request.config.getoption("--display-config")
    if path is None:
        pytest.skip("real display test requires --display-config")
    return path

def pytest_configure(config):
    config.addinivalue_line("markers", "pi_only: mark test to run only on Raspberry Pi")

def pytest_collection_modifyitems(config, items):
    # For now, don't auto-skip, just define the marker.
    # In CI, one would use pytest -m "not pi_only" on PC.
    pass
