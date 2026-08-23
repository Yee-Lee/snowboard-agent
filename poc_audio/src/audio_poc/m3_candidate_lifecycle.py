"""Bounded M3 finalist cancellation and controlled force-abort cases."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from .m3_asr import BINARY_SHA256, FIXTURE_IDS, MODEL_SHA256, PROMPT, sha256_file
from .m3_packet import TTS_PROMPT_SHA256
from .m4a_authorized_preflight import verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_tts_lifecycle import TTS_ID, run_scenario
from .m4a_whispercpp_qualification import NativeWhisperWorker


def _asr_cancel(
    binary: Path,
    model: Path,
    fixture_dir: Path,
    work_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    if sha256_file(binary) != BINARY_SHA256 or sha256_file(model) != MODEL_SHA256:
        raise ValueError("M3 ASR lifecycle artifact checksum mismatch")
    fixture = fixture_dir / f"{FIXTURE_IDS[2]}.wav"
    if not fixture.is_file():
        raise ValueError("M3 ASR cancellation fixture is unavailable")
    worker = NativeWhisperWorker(
        [
            str(binary.resolve()), "--model", str(model.resolve()), "--threads", "4",
            "--initial-prompt", PROMPT,
        ],
        work_dir / "asr-cancel.stderr.log",
        ready_timeout=timeout,
    )
    state: dict[str, Any] = {}
    entered = threading.Event()

    def transcribe() -> None:
        entered.set()
        try:
            worker.transcribe(fixture, timeout)
            state["outcome"] = "COMPLETED_BEFORE_CANCEL"
        except Exception as error:
            state["outcome"] = "CANCELLED"
            state["terminal_error_type"] = type(error).__name__

    started = time.monotonic()
    worker.start()
    thread = threading.Thread(target=transcribe, name="m3-asr-cancel", daemon=False)
    thread.start()
    entered.wait(timeout=min(timeout, 1.0))
    time.sleep(0.1)
    active_at_cancel = thread.is_alive()
    worker.terminate()
    thread.join(timeout=timeout)
    cleanup = worker.cleanup_report()
    cleanup["threads"] = int(thread.is_alive())
    cleanup["clean"] = cleanup["clean"] and not thread.is_alive()
    return {
        "candidate": "asr-whispercpp-base-q8_0-1.9.2-m2b",
        "active_at_cancel": active_at_cancel,
        "terminal_status": state.get("outcome", "NO_TERMINAL_RESULT"),
        "terminal_error_type": state.get("terminal_error_type"),
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "cleanup": cleanup,
    }


def run_candidate_lifecycle(
    repo_root: Path,
    artifact_dir: Path,
    runtime_python: Path,
    binary: Path,
    model: Path,
    fixture_dir: Path,
    work_dir: Path,
    scenario: str,
    timeout: float,
) -> dict[str, Any]:
    if work_dir.exists():
        raise ValueError("M3 candidate lifecycle work directory must be new")
    if not runtime_python.is_file():
        raise ValueError("M3 TTS lifecycle runtime Python is unavailable")
    manifest = json.loads(
        (repo_root / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text(
            encoding="utf-8"
        )
    )
    verify_candidate_inputs(manifest, TTS_ID, artifact_dir)
    prompts_path = repo_root / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(prompts_path) != TTS_PROMPT_SHA256:
        raise ValueError("tracked TTS prompt checksum mismatch")
    prompt = json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"][0]
    work_dir.mkdir(parents=True)
    model_dir = safe_extract(
        artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        work_dir,
        "matcha-icefall-zh-en",
    )
    environment = os.environ.copy()
    environment.update({
        "PYTHONPATH": str(repo_root / "poc_audio/src"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
        "NO_PROXY": "*",
    })
    base = [
        str(runtime_python), "-m", "audio_poc.m4a_tts_lifecycle_worker",
        "--model-dir", str(model_dir),
        "--vocos", str(artifact_dir / "models/vocos-16khz-univ.onnx"),
    ]
    if scenario == "cancel":
        asr = _asr_cancel(binary, model, fixture_dir, work_dir, timeout)
        tts = run_scenario(
            base, environment, "cancel", prompt,
            ready_timeout=timeout, operation_timeout=timeout, stop_timeout=timeout,
        )
        passed = (
            asr["active_at_cancel"]
            and asr["terminal_status"] == "CANCELLED"
            and asr["duration_ms"] <= timeout * 1000
            and asr["cleanup"]["clean"]
            and tts["terminal_status"] == "CANCELLED"
            and tts["duration_ms"] <= timeout * 1000
            and tts["cleanup"]["clean"]
        )
        if not passed:
            raise RuntimeError("M3 candidate cancellation did not meet the bounded cleanup gate")
        return {"scenario": scenario, "asr": asr, "tts": tts}
    if scenario == "force-abort":
        tts = run_scenario(
            base, environment, "force_abort", prompt,
            ready_timeout=timeout, operation_timeout=timeout, stop_timeout=timeout,
        )
        if not (
            tts["terminal_status"] == "FORCE_ABORTED"
            and tts["force_abort_used"]
            and tts["duration_ms"] <= timeout * 1000
            and tts["cleanup"]["clean"]
        ):
            raise RuntimeError("M3 controlled force-abort did not meet the bounded cleanup gate")
        return {"scenario": scenario, "controlled_worker": "MATCHA_GENERATE_THEN_WAIT", "tts": tts}
    raise ValueError(f"unsupported M3 candidate lifecycle scenario: {scenario}")
