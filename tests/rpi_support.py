"""Shared strict fixtures for M3 Raspberry Pi acceptance cards.

The helpers deliberately fail when a card is run without its explicit local
configuration or evidence directory.  Hardware absence is never converted to
a skip or a passing result.
"""

from __future__ import annotations

import json
import os
import hashlib
import platform
import subprocess
from pathlib import Path
from time import monotonic
from typing import Any

from sbd.core.config import load_config


def rpi_config():
    raw = os.environ.get("SBD_M3_RPI_CONFIG")
    if not raw:
        raise AssertionError("SBD_M3_RPI_CONFIG must name the sanitized Pi-local config")
    path = Path(raw)
    if not path.is_file():
        raise AssertionError("SBD_M3_RPI_CONFIG does not name a readable local config")
    return load_config(local_path=path, environ={})


def interaction_timeout() -> float:
    value = float(os.environ.get("SBD_M3_INTERACTION_TIMEOUT_SECONDS", "30"))
    if value <= 0 or value > 300:
        raise AssertionError("SBD_M3_INTERACTION_TIMEOUT_SECONDS must be in 0..300")
    return value


def require_manual(test_id: str) -> str:
    key = "SBD_M3_MANUAL_" + test_id.replace("-", "_")
    result = os.environ.get(key)
    assert result in {"PASS", "FAIL"}, f"{key}=PASS or FAIL is required after USER observation"
    assert result == "PASS", f"USER reported {test_id} manual observation as FAIL"
    return result


def record_result(test_id: str, **payload: Any) -> None:
    raw = os.environ.get("SBD_M3_EVIDENCE_DIR")
    if not raw:
        raise AssertionError("SBD_M3_EVIDENCE_DIR must point to the current candidate evidence directory")
    directory = Path(raw)
    if not directory.is_dir():
        raise AssertionError("SBD_M3_EVIDENCE_DIR must already exist")
    target = directory / f"{test_id}.json"
    config_path = Path(os.environ["SBD_M3_RPI_CONFIG"])
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    assert len(revision) == 40, "candidate revision must be a full 40-character Git SHA"
    base = {
        "test_id": test_id,
        "implementation_sha": revision,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "system": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    target.write_text(json.dumps({**base, **payload}, indent=2, sort_keys=True) + "\n")


def elapsed_samples(callback, count: int) -> list[float]:
    samples: list[float] = []
    for _ in range(count):
        started = monotonic()
        callback()
        samples.append(monotonic() - started)
    return samples
