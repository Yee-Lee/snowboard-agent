"""Bounded controller for the M3 Silero runtime worker."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Any


def run_vad_worker(
    repo_root: Path,
    runtime_python: Path,
    model: Path,
    fixture_dir: Path,
    work_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    if not runtime_python.is_file():
        raise ValueError("M3 VAD runtime Python is unavailable")
    environment = os.environ.copy()
    environment.update({
        "PYTHONPATH": str(repo_root / "poc_audio/src"),
        "PIP_NO_INDEX": "1",
        "NO_PROXY": "*",
    })
    command = [
        str(runtime_python), "-m", "audio_poc.m3_vad_worker",
        "--model", str(model),
        "--fixture-dir", str(fixture_dir),
        "--work-dir", str(work_dir),
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
        raise TimeoutError("M3 VAD worker exceeded its bounded timeout")
    if process.returncode != 0:
        raise RuntimeError(f"M3 VAD worker failed with exit {process.returncode}: {stderr[-1000:]}")
    line = next((item for item in stdout.splitlines() if item.startswith("M3_VAD_RESULT=")), None)
    if line is None:
        raise RuntimeError("M3 VAD worker did not return a result")
    result = json.loads(line.removeprefix("M3_VAD_RESULT="))
    if result.get("bounded_fixture_count") < 5:
        result["review_disposition"] = "MISSING_SPEECH_EVENT_REVIEW_REQUIRED"
    result["_result_disposition"] = "INCONCLUSIVE"
    return result
