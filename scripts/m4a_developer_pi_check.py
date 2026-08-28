"""Sanitized Developer-only Raspberry Pi M4a pre-submit diagnostics.

This is not the formal Tester acceptance runner.  It exercises the real
installed ASR/TTS/ALSA paths and prints only bounded metrics suitable for a
Developer diagnostic record.  The runbook owns clean-device, fresh-product and
offline-network-namespace setup.
"""

from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"

import argparse
import asyncio
import json
import tempfile
import time
import wave
from pathlib import Path
from typing import Any

from sbd.action.speak import make_tts_adapter
from sbd.adaptor.errors import AdapterRejected
from sbd.adaptor.framed_child import ChildState
from sbd.core.audio import make_audio_output
from sbd.core.config import load_config
from sbd.perception.listen import make_asr_adapter


FRAME_BYTES = 640
TTS_FIXTURE = "這是離線語音產品驗證。"


def _assert_offline_namespace() -> None:
    interfaces = []
    for line in Path("/proc/net/dev").read_text(encoding="ascii").splitlines()[2:]:
        if ":" in line:
            name = line.split(":", 1)[0].strip()
            if name and name != "lo":
                interfaces.append(name)
    assert interfaces == [], f"non-loopback interfaces present: {interfaces}"
    route = Path("/proc/net/route")
    if route.is_file():
        default_routes = [
            fields
            for line in route.read_text(encoding="ascii").splitlines()[1:]
            if len(fields := line.split()) >= 2
            and fields[0] != "lo"
            and fields[1] == "00000000"
        ]
        assert default_routes == [], "default route present in diagnostic namespace"


def _child_pids() -> set[int]:
    own = os.getpid()
    parents: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
            parents[int(entry.name)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            continue
    found: set[int] = set()
    frontier = {own}
    while frontier:
        children = {pid for pid, parent in parents.items() if parent in frontier and pid not in found}
        found.update(children)
        frontier = children
    return found


def _snapshot() -> tuple[set[int], int, int, int]:
    own = Path("/proc") / str(os.getpid())
    temp_entries = 0
    for name in ("sbd-m4a-asr", "sbd-m4a-tts"):
        root = Path(tempfile.gettempdir()) / name
        if root.is_dir():
            temp_entries += len(list(root.iterdir()))
    return (
        _child_pids(),
        len(list((own / "task").iterdir())),
        len(list((own / "fd").iterdir())),
        temp_entries,
    )


def _delta(before: tuple[set[int], int, int, int]) -> dict[str, int]:
    before_children, before_threads, before_fds, before_temp = before
    after_children, after_threads, after_fds, after_temp = _snapshot()
    return {
        "orphan_processes": len(after_children - before_children),
        "thread_leaks": max(0, after_threads - before_threads),
        "fd_leaks": max(0, after_fds - before_fds),
        "temp_leaks": max(0, after_temp - before_temp),
    }


async def _wav_frames(path: Path):
    with wave.open(str(path), "rb") as source:
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert source.getframerate() == 16_000
        while frame := source.readframes(FRAME_BYTES // 2):
            assert len(frame) == FRAME_BYTES
            yield frame


async def _silence_frame():
    yield b"\x00" * FRAME_BYTES


async def _transcribe(asr: Any, path: Path) -> float:
    frames = _wav_frames(path)
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(asr.transcribe(frames), timeout=90)
    finally:
        await frames.aclose()
    assert isinstance(result.text, str) and result.text.strip()
    assert result.language == "zh-TW"
    return round((time.monotonic() - started) * 1000, 3)


async def _asr(config: Any, pcm: Path) -> dict[str, Any]:
    before = _snapshot()
    asr = make_asr_adapter(config.perception.listen.adapter)
    await asr.start()
    try:
        latencies = [await _transcribe(asr, pcm), await _transcribe(asr, pcm)]
        assert asr.state is ChildState.READY
        started = time.monotonic()
        try:
            await asyncio.wait_for(asr.transcribe(_silence_frame()), timeout=15)
        except AdapterRejected as exc:
            assert "ended before an endpoint" in str(exc)
        else:
            raise AssertionError("finite silence unexpectedly produced a transcript")
        no_endpoint_ms = round((time.monotonic() - started) * 1000, 3)
        assert asr.state is ChildState.READY
    finally:
        if asr.state is ChildState.BUSY:
            await asr.force_abort()
        elif asr.state is ChildState.READY:
            await asr.stop()
    assert asr.state is ChildState.STOPPED
    await asyncio.sleep(0.1)
    cleanup = _delta(before)
    assert all(value == 0 for value in cleanup.values()), cleanup
    return {
        "case": "asr-two-turn-finite-eof-noendpoint",
        "cleanup": cleanup,
        "latency_ms": latencies,
        "no_endpoint_ms": no_endpoint_ms,
        "result_nonempty": True,
        "state": asr.state.name,
    }


async def _drain(tts: Any, output: Any) -> int:
    byte_count = 0

    async def measured():
        nonlocal byte_count
        async for chunk in tts.synthesize(TTS_FIXTURE):
            assert chunk and len(chunk) <= FRAME_BYTES and len(chunk) % 2 == 0
            byte_count += len(chunk)
            yield chunk

    await asyncio.wait_for(output.play(measured()), timeout=90)
    assert byte_count > 0
    return byte_count


async def _tts(config: Any) -> dict[str, Any]:
    controller_threads = len(
        list((Path("/proc") / str(os.getpid()) / "task").iterdir()),
    )
    assert controller_threads == 1, (
        f"controller imported audio stack with {controller_threads} native threads"
    )
    before = _snapshot()
    tts = make_tts_adapter(config.action.tts)
    output = make_audio_output(config.core.audio)
    await tts.start()
    await output.start()
    try:
        played_bytes = await _drain(tts, output)
    finally:
        await output.stop()
        await tts.stop()

    tts = make_tts_adapter(config.action.tts)
    await tts.start()
    child = tts._child
    invalid_id = child.allocate_request_id()
    await child.send({
        "protocol": 1,
        "op": "GENERATE",
        "request_id": invalid_id,
        "text": "",
        "voice_id": "matcha-zh-en-default-sid-0",
    })
    error = await asyncio.wait_for(child.receive(), timeout=5)
    assert error == {
        "protocol": 1,
        "event": "ERROR",
        "request_id": invalid_id,
        "code": "INVALID_TEXT",
    }
    child.operation_finished()

    cancel_id = child.allocate_request_id()
    await child.send({
        "protocol": 1,
        "op": "GENERATE",
        "request_id": cancel_id,
        "text": TTS_FIXTURE * 200,
        "voice_id": "matcha-zh-en-default-sid-0",
    })
    await child.send({"protocol": 1, "op": "CANCEL", "request_id": cancel_id})
    deferred = await asyncio.wait_for(child.receive(), timeout=5)
    assert deferred == {
        "protocol": 1,
        "event": "CANCEL_DEFERRED",
        "request_id": cancel_id,
    }
    pending = asyncio.create_task(child.receive())
    level1_seconds = config.cancel.abort_timeout_seconds.by_kind.get(
        "action.speak", config.cancel.abort_timeout_seconds.default,
    )
    done, _ = await asyncio.wait({pending}, timeout=level1_seconds)
    assert not done
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    report = await tts.force_abort()
    assert report.destroyed_backends == ("backend.action.speak.tts",)
    assert tts.state is ChildState.DESTROYED
    await tts.rebuild(None, config)
    recovery_bytes = []
    for _ in range(2):
        chunks = [chunk async for chunk in tts.synthesize(TTS_FIXTURE)]
        assert chunks
        recovery_bytes.append(sum(map(len, chunks)))
    await tts.stop()
    assert tts.state is ChildState.STOPPED
    await asyncio.sleep(0.1)
    cleanup = _delta(before)
    assert all(value == 0 for value in cleanup.values()), cleanup
    return {
        "case": "tts-alsa-deferred-level2-rebuild",
        "cleanup": cleanup,
        "openblas_threads": os.environ["OPENBLAS_NUM_THREADS"],
        "controller_threads": controller_threads,
        "played_bytes": played_bytes,
        "recovery_bytes": recovery_bytes,
        "state": tts.state.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("asr", "tts"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--pcm", type=Path)
    args = parser.parse_args()
    _assert_offline_namespace()
    config = load_config(local_path=args.config, dotenv_path=Path(os.devnull), environ={})
    if args.mode == "asr":
        assert args.pcm is not None
        result = asyncio.run(_asr(config, args.pcm))
    else:
        result = asyncio.run(_tts(config))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
