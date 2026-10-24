"""M4A-OFF-001 — target offline collector and no-downloader support."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("telemetry", ["0", "false", "yes"])
def test_m4a_off_001_child_environment_forces_offline_and_removes_proxies(
    monkeypatch: pytest.MonkeyPatch,
    telemetry: str,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "M4A_PRIVATE_CREDENTIAL_SENTINEL")
    environment = _offline_environment()
    assert environment["PIP_NO_INDEX"] == "1"
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert not any(name.lower().endswith("_proxy") for name in environment)
    child = offline_child_environment({
        "HTTPS_PROXY": "secret",
        "KEEP": "value",
        "ORT_DISABLE_TELEMETRY": telemetry,
    })
    assert child["PYTHONNOUSERSITE"] == "1" and child["PIP_NO_INDEX"] == "1"
    assert child["ORT_DISABLE_TELEMETRY"] == "1"
    assert child["KEEP"] == "value"
    assert not any(name.lower().endswith("_proxy") for name in child)


CHILD_INITIALIZER_PROBES = {
    "asr": """
import os
import sys
import types

numpy = types.ModuleType("numpy")
numpy.float32 = object()
numpy.zeros = lambda shape, dtype: (shape, dtype)

class Options:
    intra_op_num_threads = 0
    inter_op_num_threads = 0

class Session:
    def get_inputs(self):
        return [types.SimpleNamespace(name=name) for name in ("input", "state", "sr")]

def initialize(*args, **kwargs):
    assert os.environ["ORT_DISABLE_TELEMETRY"] == "1"
    return Session()

ort = types.ModuleType("onnxruntime")
ort.SessionOptions = Options
ort.InferenceSession = initialize
sys.modules["numpy"] = numpy
sys.modules["onnxruntime"] = ort

from sbd.perception.listen.whispercpp import supervisor
supervisor.require_runtime_identity = lambda: None
supervisor.Silero("vad.onnx")
""",
    "tts": """
import os
import sys
import types
from pathlib import Path

class Config:
    def __init__(self, **kwargs):
        pass
    def validate(self):
        return True

def initialize(config):
    assert os.environ["ORT_DISABLE_TELEMETRY"] == "1"
    return object()

sherpa = types.ModuleType("sherpa_onnx")
sherpa.OfflineTtsConfig = Config
sherpa.OfflineTtsModelConfig = Config
sherpa.OfflineTtsMatchaModelConfig = Config
sherpa.OfflineTts = initialize
sys.modules["sherpa_onnx"] = sherpa

from sbd.action.speak.matcha import worker
worker.require_runtime_identity = lambda: None
worker.load_tts(Path("model"), Path("vocoder.onnx"))
""",
}


@pytest.mark.parametrize("child", sorted(CHILD_INITIALIZER_PROBES))
def test_m4a_off_001_direct_child_forces_telemetry_off_before_native_init(
    child: str,
) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    environment["ORT_DISABLE_TELEMETRY"] = "0"
    completed = subprocess.run(
        [sys.executable, "-c", CHILD_INITIALIZER_PROBES[child]],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
