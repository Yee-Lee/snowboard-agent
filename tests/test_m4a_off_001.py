"""M4A-OFF-001 — target offline collector and no-downloader support."""

from __future__ import annotations

from scripts.m4a_audio_product import _offline_environment
from scripts.m4a_target_metrics import network_isolated
from sbd.adaptor.framed_child import offline_child_environment


NET_DEV_LOOPBACK = """Inter-| Receive\n face |bytes\n    lo: 1 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0\n"""
ROUTE_EMPTY = "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"


def test_m4a_off_001_loopback_only_namespace_is_accepted() -> None:
    assert network_isolated(NET_DEV_LOOPBACK, ROUTE_EMPTY) is True


def test_m4a_off_001_nonloopback_interface_or_default_route_is_rejected() -> None:
    ethernet = NET_DEV_LOOPBACK + "  eth0: 1 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0\n"
    route = ROUTE_EMPTY + "eth0 00000000 01020304 0003 0 0 0 00000000 0 0 0\n"
    assert network_isolated(ethernet, ROUTE_EMPTY) is False
    assert network_isolated(NET_DEV_LOOPBACK, route) is False


def test_m4a_off_001_child_environment_forces_offline_and_removes_proxies(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "M4A_PRIVATE_CREDENTIAL_SENTINEL")
    environment = _offline_environment()
    assert environment["PIP_NO_INDEX"] == "1"
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert not any(name.lower().endswith("_proxy") for name in environment)
    child = offline_child_environment({"HTTPS_PROXY": "secret", "KEEP": "value"})
    assert child["PYTHONNOUSERSITE"] == "1" and child["PIP_NO_INDEX"] == "1"
    assert child["KEEP"] == "value"
    assert not any(name.lower().endswith("_proxy") for name in child)
