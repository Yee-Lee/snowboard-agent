"""M4B-OFF-001 — allowlisted child environment and network oracle."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.m4b_target_metrics import network_isolated
from sbd.cognition.litert_lm.adapter import isolated_child_environment
from sbd.cognition.litert_lm.worker import _verify_native_library


def test_m4b_off_001_environment_removes_import_network_and_loader_escape() -> None:
    env = isolated_child_environment(Path("/verified/runtime"), {
        "PYTHONPATH": "/private", "PYTHONHOME": "/private", "LD_PRELOAD": "/private/lib.so",
        "HTTPS_PROXY": "http://private", "SAFE": "yes",
    })
    assert env["PYTHONNOUSERSITE"] == "1" and env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PIP_NO_INDEX"] == "1" and env["LD_LIBRARY_PATH"] == "/verified/runtime/litert_lm"
    assert "PYTHONPATH" not in env and "PYTHONHOME" not in env and "LD_PRELOAD" not in env
    assert all(not key.lower().endswith("_proxy") for key in env)


def test_m4b_off_001_network_namespace_oracle_requires_loopback_only() -> None:
    assert network_isolated("h1\nh2\n lo: 0\n", "Iface Destination\nlo 00000000\n")
    assert not network_isolated("h1\nh2\n eth0: 0\n", "Iface Destination\n")


def test_m4b_off_001_native_bytes_are_verified_before_runtime_import(tmp_path: Path) -> None:
    native = tmp_path / "liblitert-lm.so"
    native.write_bytes(b"authenticated-native")
    _verify_native_library(native, hashlib.sha256(native.read_bytes()).hexdigest())
    with pytest.raises(RuntimeError, match="native runtime identity"):
        _verify_native_library(native, "0" * 64)
    native.unlink()
    native.symlink_to(tmp_path / "missing")
    with pytest.raises(RuntimeError, match="native runtime identity"):
        _verify_native_library(native, "0" * 64)
