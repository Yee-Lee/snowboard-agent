"""Generate the six frozen Matcha prompts in a bounded worker and play through Core."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
from pathlib import Path
from typing import Any

from .m3_core_hal import play_stream_pcm
from .m3_packet import TTS_IDS, TTS_PROMPT_SHA256
from .m4a_authorized_preflight import verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_tts_lifecycle import TTS_ID, sha256_file


async def _read_json_line(stream: asyncio.StreamReader, timeout: float) -> dict[str, Any]:
    line = await asyncio.wait_for(stream.readline(), timeout=timeout)
    if not line:
        raise RuntimeError("Matcha worker closed its protocol stream")
    document = json.loads(line)
    if not isinstance(document, dict):
        raise RuntimeError("Matcha worker returned a non-object event")
    return document


async def _terminate(process: asyncio.subprocess.Process, timeout: float) -> None:
    if process.returncode is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=min(timeout, 5.0))
    except TimeoutError:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


async def run_matcha_playback(
    runtime_python: Path,
    model_dir: Path,
    vocos: Path,
    prompts: list[dict[str, Any]],
    audio: Any,
    config: Any,
    timeout: float,
    pythonpath: Path,
    worker_module: str = "audio_poc.m3_tts_worker",
) -> list[dict[str, Any]]:
    environment = os.environ.copy()
    environment.update({
        "PYTHONPATH": str(pythonpath),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
        "NO_PROXY": "*",
    })
    process = await asyncio.create_subprocess_exec(
        str(runtime_python), "-m", worker_module,
        "--model-dir", str(model_dir), "--vocos", str(vocos),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=environment,
        start_new_session=True,
    )
    assert process.stdin is not None and process.stdout is not None
    records: list[dict[str, Any]] = []
    try:
        ready = await _read_json_line(process.stdout, timeout)
        if ready.get("event") != "READY":
            raise RuntimeError(f"Matcha worker did not become READY: {ready.get('event')}")
        for prompt in prompts:
            command = {
                "op": "GENERATE",
                "fixture_id": prompt["fixture_id"],
                "text": prompt["text"],
            }
            process.stdin.write(json.dumps(command, ensure_ascii=False).encode("utf-8") + b"\n")
            await process.stdin.drain()
            header = await _read_json_line(process.stdout, timeout)
            if header.get("event") != "PCM" or header.get("fixture_id") != prompt["fixture_id"]:
                raise RuntimeError(f"Matcha worker PCM protocol failed: {header.get('event')}")
            pcm_bytes = int(header.get("pcm_bytes", 0))
            if pcm_bytes <= 0 or pcm_bytes % 2:
                raise RuntimeError("Matcha worker returned invalid PCM length")
            pcm = await asyncio.wait_for(process.stdout.readexactly(pcm_bytes), timeout=timeout)
            observed = hashlib.sha256(pcm).hexdigest()
            if observed != header.get("pcm_sha256"):
                raise RuntimeError("Matcha worker PCM checksum mismatch")
            await play_stream_pcm(audio.make_audio_output(config), pcm, timeout)
            records.append({
                "fixture_id": prompt["fixture_id"],
                "category": prompt["category"],
                "text_sha256": hashlib.sha256(prompt["text"].encode("utf-8")).hexdigest(),
                "pcm_sha256": observed,
                "sample_count": header["sample_count"],
                "duration_seconds": round(int(header["sample_count"]) / 16_000, 6),
                "playback_complete": True,
            })
        process.stdin.write(b'{"op":"SHUTDOWN"}\n')
        await process.stdin.drain()
        ack = await _read_json_line(process.stdout, timeout)
        if ack.get("event") != "SHUTDOWN_ACK":
            raise RuntimeError("Matcha worker did not acknowledge shutdown")
        if await asyncio.wait_for(process.wait(), timeout=timeout) != 0:
            raise RuntimeError("Matcha worker returned a nonzero exit status")
        return records
    finally:
        await _terminate(process, timeout)


async def prepare_and_run_matcha(
    repo_root: Path,
    artifact_dir: Path,
    work_dir: Path,
    runtime_python: Path,
    audio: Any,
    config: Any,
    timeout: float,
) -> dict[str, Any]:
    if work_dir.exists():
        raise ValueError("Matcha work directory must be new")
    if not runtime_python.is_file():
        raise ValueError("Matcha runtime Python is unavailable")
    manifest = json.loads(
        (repo_root / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text(encoding="utf-8")
    )
    verified = verify_candidate_inputs(manifest, TTS_ID, artifact_dir)
    prompts_path = repo_root / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(prompts_path) != TTS_PROMPT_SHA256:
        raise ValueError("tracked TTS prompt checksum mismatch")
    by_id = {
        item["fixture_id"]: item
        for item in json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"]
    }
    prompts = [by_id[fixture_id] for fixture_id in TTS_IDS]
    work_dir.mkdir(parents=True)
    model = safe_extract(
        artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        work_dir,
        "matcha-icefall-zh-en",
    )
    records = await run_matcha_playback(
        runtime_python,
        model,
        artifact_dir / "models/vocos-16khz-univ.onnx",
        prompts,
        audio,
        config,
        timeout,
        repo_root / "poc_audio/src",
    )
    return {
        "_result_disposition": "INCONCLUSIVE",
        "review_disposition": "PENDING_USER_LISTENING_SCORE_AND_CRITICAL_MISREAD_REVIEW",
        "candidate_id": TTS_ID,
        "prompt_count": len(records),
        "prompt_ids": list(TTS_IDS),
        "verified_artifacts": [item.to_dict() for item in verified],
        "records": records,
        "pcm_contract": "16000_HZ_MONO_S16_LE_TO_CORE_AUDIOOUTPUT",
    }
