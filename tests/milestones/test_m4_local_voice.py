"""M4a exact-product Raspberry Pi local-voice acceptance suite.

The suite is intentionally fail-closed: the Tester supplies a frozen candidate
SHA, sanitized real-driver config, controlled 16 kHz mono S16_LE speech PCM,
and a fresh card directory through environment variables.  Missing target
inputs fail; formal acceptance never converts them to Skip/Pending.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import os
import platform
import re
import threading
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from sbd.action.speak import make_tts_adapter
from sbd.adaptor.errors import AdapterRejected
from sbd.adaptor.framed_child import ChildState
from sbd.core.audio import make_audio_output
from sbd.core.config import load_config
from sbd.perception.listen import make_asr_adapter
from sbd.perception.listen.whispercpp.supervisor import PROMPT as ASR_PROMPT
from scripts.m4a_target_metrics import (
    descendants,
    network_isolated,
    privacy_hits,
    system_used_mib,
)


pytestmark = pytest.mark.rpi
SHA40 = re.compile(r"^[0-9a-f]{40}$")
TTS_FIXTURE = "這是離線語音產品驗證。"
_PRIVATE_SENTINELS: set[str] = {TTS_FIXTURE, ASR_PROMPT}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is required for M4a target acceptance"
    return value


def _inputs() -> tuple[str, Any, Path, Path]:
    candidate = _required_env("SBD_M4A_CANDIDATE_SHA")
    assert SHA40.fullmatch(candidate), "candidate SHA must be frozen lowercase 40-hex"
    run_id = _required_env("SBD_M4A_ACCEPTANCE_RUN_ID")
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", run_id)
    _PRIVATE_SENTINELS.add(_required_env("SBD_M4A_PRIVACY_SENTINEL"))
    runner_preflight_path = Path(_required_env("SBD_M4A_RUNNER_PREFLIGHT")).resolve()
    assert runner_preflight_path.is_file() and not runner_preflight_path.is_symlink()
    runner_preflight = json.loads(runner_preflight_path.read_text(encoding="utf-8"))
    assert runner_preflight["candidate_sha"] == candidate
    assert runner_preflight["run_id"] == run_id
    assert runner_preflight["status"] == "Pass"
    product_reference = runner_preflight["checksums"]["artifact_manifest"]
    product_preflight_path = Path(product_reference["path"]).resolve()
    assert product_preflight_path.is_file() and not product_preflight_path.is_symlink()
    assert hashlib.sha256(product_preflight_path.read_bytes()).hexdigest() == product_reference["sha256"]
    product_preflight = json.loads(product_preflight_path.read_text(encoding="utf-8"))
    assert product_preflight["status"] == "Pass"
    assert product_preflight["operation"] == "preflight"
    assert product_preflight["candidate_sha"] == candidate
    assert product_preflight["accepted_audio_sha"] == "5694ead4ba6be928fdb4dbdf6da7155b214d72bd"
    assert product_preflight["install_schema"] == "sbd.m4a.product-install.v4"
    assert product_preflight["matcha_tree_sha256"] == "5e4f8625f9f7d62f9a410d33571ebcd1e3e5b8b0f43f1ebda23512a79e2f3319"
    assert re.fullmatch(r"[0-9a-f]{64}", product_preflight["notice_sha256"])
    assert product_preflight["network_attempt_count"] == 0
    assert platform.machine() == "aarch64", "M4a acceptance requires Linux aarch64"
    config_path = Path(_required_env("SBD_M4A_TARGET_CONFIG")).resolve()
    pcm_path = Path(_required_env("SBD_M4A_ASR_PCM")).resolve()
    card_root = Path(_required_env("SBD_M4A_CARD_ROOT")).resolve()
    assert config_path.is_file() and not config_path.is_symlink()
    assert pcm_path.is_file() and not pcm_path.is_symlink()
    assert card_root.is_dir() and not card_root.is_symlink()
    assert card_root.name == "cards", "formal card root must be runner-owned"
    config = load_config(local_path=config_path, dotenv_path=Path(os.devnull), environ={})
    assert config.perception.listen.adapter.driver == "whispercpp"
    assert config.action.tts.driver == "sherpa_matcha"
    assert config.core.audio.driver == "alsa"
    size = pcm_path.stat().st_size
    assert 0 < size <= 60 * 16000 * 2 and size % 640 == 0
    return candidate, config, pcm_path, card_root


def _write_card(root: Path, test_id: str, candidate: str, **metrics: Any) -> None:
    # This is an unsigned metric draft.  candidate_gate.py owns and adds every
    # formal runner field only after the complete acceptance suite is green.
    card = {
        "candidate_sha": candidate,
        "test_id": test_id,
        **metrics,
    }
    path = root / f"{test_id}.json"
    with path.open("x", encoding="utf-8") as target:
        json.dump(card, target, indent=2, sort_keys=True)
        target.write("\n")


async def _pcm_frames(path: Path):
    with path.open("rb") as source:
        while frame := source.read(640):
            assert len(frame) == 640
            yield frame


async def _transcribe(asr: Any, path: Path) -> tuple[str, float]:
    frames = _pcm_frames(path)
    started = time.monotonic()
    try:
        result = await asr.transcribe(frames)
    finally:
        await frames.aclose()
    latency_ms = (time.monotonic() - started) * 1000
    assert isinstance(result.text, str) and result.text.strip()
    assert result.language == "zh-TW"
    _PRIVATE_SENTINELS.add(result.text)
    return result.text, latency_ms


async def _wait_state(owner: Any, state: ChildState, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while owner.state is not state and time.monotonic() < deadline:
        await asyncio.sleep(0.001)
    assert owner.state is state


async def _drain_tts(tts: Any, output: Any) -> tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0

    async def measured():
        nonlocal byte_count
        async for chunk in tts.synthesize(TTS_FIXTURE):
            assert 0 < len(chunk) <= 640 and len(chunk) % 2 == 0
            digest.update(chunk)
            byte_count += len(chunk)
            yield chunk

    await output.play(measured())
    assert byte_count > 0 and byte_count <= 64 * 1024 * 1024
    return digest.hexdigest(), byte_count


def test_m4a_asr_001_and_002_real_persistent_two_turns() -> None:
    candidate, config, pcm_path, cards = _inputs()

    async def run() -> None:
        before = _cleanup_snapshot()
        asr = make_asr_adapter(config.perception.listen.adapter)
        await asr.start()
        try:
            _, first_latency = await _transcribe(asr, pcm_path)
            _, second_latency = await _transcribe(asr, pcm_path)
            assert asr.state is ChildState.READY
        finally:
            await asr.stop()
        assert all(value == 0 for value in _cleanup_delta(before).values())
        _write_card(cards, "M4A-ASR-001", candidate, latency_ms=round(first_latency, 3))
        _write_card(cards, "M4A-ASR-002", candidate, turn_count=2, max_latency_ms=round(max(first_latency, second_latency), 3))

    asyncio.run(run())


def test_m4a_asr_003_actual_process_group_destroy_and_recovery() -> None:
    candidate, config, pcm_path, cards = _inputs()

    async def run() -> None:
        before = _cleanup_snapshot()
        asr = make_asr_adapter(config.perception.listen.adapter)
        await asr.start()

        # Actual supervisor cooperative capture cancellation.
        hold = asyncio.Event()
        capture_waiting = asyncio.Event()

        async def capture_then_hold():
            with pcm_path.open("rb") as source:
                yield source.read(640)
            capture_waiting.set()
            await hold.wait()

        capture = asyncio.create_task(asr.transcribe(capture_then_hold()))
        await asyncio.wait_for(capture_waiting.wait(), timeout=5)
        await _wait_state(asr, ChildState.BUSY)
        await asyncio.wait_for(asr.abort(), timeout=5)
        assert asr.state is ChildState.READY
        with pytest.raises(AdapterRejected, match="cancelled"):
            await capture

        # A real inference is interrupted at Level 2, proving PGID cleanup.
        inference = asyncio.create_task(asr.transcribe(_pcm_frames(pcm_path)))
        await _wait_state(asr, ChildState.BUSY)
        await asyncio.sleep(0.1)
        assert not inference.done(), "controlled fixture must reach real whisper inference"
        inference.cancel()
        with pytest.raises(asyncio.CancelledError):
            await inference
        report = await asr.force_abort()
        assert report.destroyed_backends == ("backend.perception.listen.asr",)
        assert asr.state is ChildState.DESTROYED
        await asr.rebuild(None, config)
        await _transcribe(asr, pcm_path)
        await asr.stop()
        assert asr.state is ChildState.STOPPED
        cleanup = _cleanup_delta(before)
        assert all(value == 0 for value in cleanup.values())
        _write_card(
            cards, "M4A-ASR-003", candidate,
            case="actual-cancel-timeout-sigterm-rebuild",
            cleanup_count=sum(cleanup.values()), cleanup=cleanup,
        )

    asyncio.run(run())


def test_m4a_tts_001_real_pcm_and_audio_output_drain() -> None:
    candidate, config, _, cards = _inputs()

    async def run() -> None:
        before = _cleanup_snapshot()
        tts = make_tts_adapter(config.action.tts)
        output = make_audio_output(config.core.audio)
        await tts.start()
        await output.start()
        try:
            pcm_sha256, payload_bytes = await _drain_tts(tts, output)
        finally:
            await output.stop()
            await tts.stop()
        assert all(value == 0 for value in _cleanup_delta(before).values())
        _write_card(
            cards, "M4A-TTS-001", candidate,
            pcm_sha256=pcm_sha256, sample_rate_hz=16000, channels=1,
            sample_format="S16_LE", payload_bytes=payload_bytes,
        )

    asyncio.run(run())


def test_m4a_tts_002_actual_process_group_destroy_and_recovery() -> None:
    candidate, config, _, cards = _inputs()

    async def run() -> None:
        before = _cleanup_snapshot()
        tts = make_tts_adapter(config.action.tts)
        await tts.start()

        # Inject an invalid request at the actual child wire boundary, then
        # prove that the same loaded engine reopens for another request.
        child = tts._child
        invalid_id = child.allocate_request_id()
        await child.send({
            "protocol": 1, "op": "GENERATE", "request_id": invalid_id,
            "text": "", "voice_id": "matcha-zh-en-default-sid-0",
        })
        error = await asyncio.wait_for(child.receive(), timeout=5)
        assert error == {
            "protocol": 1, "event": "ERROR", "request_id": invalid_id,
            "code": "INVALID_TEXT",
        }
        child.operation_finished()

        # Actual Matcha cooperative cancellation must produce a terminal and
        # return the same persistent child to READY.
        cancel_text = TTS_FIXTURE * 200
        cancel_id = child.allocate_request_id()
        await child.send({
            "protocol": 1, "op": "GENERATE", "request_id": cancel_id,
            "text": cancel_text, "voice_id": "matcha-zh-en-default-sid-0",
        })
        await child.send({"protocol": 1, "op": "CANCEL", "request_id": cancel_id})
        deferred = await asyncio.wait_for(child.receive(), timeout=5)
        assert deferred == {
            "protocol": 1, "event": "CANCEL_DEFERRED", "request_id": cancel_id,
        }
        cancelled = await asyncio.wait_for(
            child.receive(), timeout=config.action.tts.child_ready_timeout_seconds,
        )
        assert cancelled == {
            "protocol": 1, "event": "CANCELLED", "request_id": cancel_id,
        }
        child.operation_finished()

        # Level-1 timeout cannot become success; Level 2 destroys the actual
        # process group while generation is active.
        timed_generator = tts.synthesize(cancel_text)
        timed = asyncio.create_task(anext(timed_generator))
        await _wait_state(tts, ChildState.BUSY)
        timed.cancel()
        with pytest.raises(asyncio.CancelledError):
            await timed
        report = await tts.force_abort()
        assert report.destroyed_backends == ("backend.action.speak.tts",)
        assert tts.state is ChildState.DESTROYED
        await tts.rebuild(None, config)
        first = [chunk async for chunk in tts.synthesize(TTS_FIXTURE)]
        second = [chunk async for chunk in tts.synthesize(TTS_FIXTURE)]
        assert first and second and tts.state is ChildState.READY
        await tts.stop()
        cleanup = _cleanup_delta(before)
        assert all(value == 0 for value in cleanup.values())
        _write_card(
            cards, "M4A-TTS-002", candidate,
            case="actual-error-cancel-timeout-sigterm-rebuild",
            cleanup_count=sum(cleanup.values()), cleanup=cleanup,
        )

    asyncio.run(run())


def _network_isolated() -> bool:
    return network_isolated(
        Path("/proc/net/dev").read_text(encoding="ascii"),
        Path("/proc/net/route").read_text(encoding="ascii"),
    )


def _system_used_mib() -> float:
    return system_used_mib(Path("/proc/meminfo").read_text(encoding="ascii"))


def _child_pids() -> set[int]:
    own = os.getpid()
    parents: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (
                (entry / "stat").read_text(encoding="ascii")
                .rsplit(")", 1)[1].split()
            )
            parents[int(entry.name)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            continue
    return descendants(parents, own)


def _cleanup_snapshot() -> tuple[set[int], int, int, int]:
    threads = len(list((Path("/proc") / str(os.getpid()) / "task").iterdir()))
    fds = len(list((Path("/proc") / str(os.getpid()) / "fd").iterdir()))
    temp_entries = 0
    temp_root = Path(tempfile.gettempdir())
    for name in ("sbd-m4a-asr", "sbd-m4a-tts"):
        root = temp_root / name
        if root.is_dir():
            temp_entries += len(list(root.iterdir()))
    return _child_pids(), threads, fds, temp_entries


def _cleanup_delta(before: tuple[set[int], int, int, int]) -> dict[str, int]:
    before_children, before_threads, before_fds, before_temp = before
    after_children, after_threads, after_fds, after_temp = _cleanup_snapshot()
    return {
        "orphan_processes": len(after_children - before_children),
        "thread_leaks": max(0, after_threads - before_threads),
        "fd_leaks": max(0, after_fds - before_fds),
        "temp_leaks": max(0, after_temp - before_temp),
    }


def _descendant_socket_count() -> int:
    count = 0
    for pid in _child_pids():
        fd_root = Path("/proc") / str(pid) / "fd"
        try:
            for fd in fd_root.iterdir():
                try:
                    if fd.readlink().as_posix().startswith("socket:["):
                        count += 1
                except OSError:
                    continue
        except OSError:
            continue
    return count


def _thermal_status() -> str:
    try:
        completed = subprocess.run(
            ["vcgencmd", "get_throttled"], text=True, capture_output=True, check=False,
        )
    except OSError:
        return "unavailable"
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else "unavailable"


def test_m4a_off_001_and_res_001_offline_audio_only_envelope() -> None:
    candidate, config, pcm_path, cards = _inputs()
    assert _network_isolated(), "acceptance must run in a loopback-only network namespace"
    cleanup_before = _cleanup_snapshot()
    peaks: list[float] = []
    socket_counts: list[int] = []
    stop_sampling = threading.Event()

    def sample_memory() -> None:
        while not stop_sampling.wait(0.01):
            peaks.append(_system_used_mib())
            socket_counts.append(_descendant_socket_count())

    sampler = threading.Thread(target=sample_memory, name="m4a-memory-sampler")
    sampler.start()

    turn_count = int(os.environ.get("SBD_M4A_RESOURCE_TURNS", "20"))
    assert turn_count >= 20

    async def session() -> tuple[list[float], str]:
        asr = make_asr_adapter(config.perception.listen.adapter)
        tts = make_tts_adapter(config.action.tts)
        output = make_audio_output(config.core.audio)
        await asr.start(); await tts.start(); await output.start()
        try:
            latencies = []
            pcm_sha256 = ""
            for _ in range(turn_count):
                started = time.monotonic()
                await _transcribe(asr, pcm_path)
                pcm_sha256, _ = await _drain_tts(tts, output)
                latencies.append((time.monotonic() - started) * 1000)
            return latencies, pcm_sha256
        finally:
            await output.stop(); await tts.stop(); await asr.stop()

    try:
        latencies_ms, _ = asyncio.run(session())
    finally:
        stop_sampling.set()
        sampler.join(timeout=2)
    peak = max(peaks or [_system_used_mib()])
    cleanup = _cleanup_delta(cleanup_before)
    orphan_count = cleanup["orphan_processes"]
    assert peak <= 3584
    assert all(value == 0 for value in cleanup.values())
    assert max(socket_counts or [0]) == 0
    ordered = sorted(latencies_ms)
    p99_latency_ms = ordered[math.ceil(0.99 * len(ordered)) - 1]
    _write_card(cards, "M4A-OFF-001", candidate, network_attempts=0, downloader_calls=0, session_result="Pass")
    _write_card(cards, "M4A-RES-001", candidate, p99_latency_ms=round(p99_latency_ms, 3), peak_system_used_mib=round(peak, 3), orphan_count=orphan_count, cleanup=cleanup, thermal_status=_thermal_status(), turn_count=turn_count)


def test_m4a_pkg_001_installed_product_manifest_matches_live_config() -> None:
    candidate, config, _, cards = _inputs()
    install_root = Path(_required_env("SBD_M4A_INSTALL_ROOT")).resolve()
    manifest_path = install_root / "install-manifest.json"
    assert manifest_path.is_file() and not manifest_path.is_symlink()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "sbd.m4a.product-install.v4"
    assert manifest["matcha_tree_sha256"] == "5e4f8625f9f7d62f9a410d33571ebcd1e3e5b8b0f43f1ebda23512a79e2f3319"
    notice = install_root / "notices" / "THIRD_PARTY_NOTICES.md"
    assert _sha256(notice) == manifest["notice_sha256"]
    assert len(manifest["vad_distributions"]) == 5
    assert len(manifest["tts_distributions"]) == 3
    assert config.perception.listen.adapter.worker_path.is_relative_to(install_root)
    assert config.action.tts.runtime_python.is_relative_to(install_root)
    _write_card(cards, "M4A-PKG-001", candidate, install_root=install_root.name, wheel_count=8)


def test_m4a_priv_001_scan_product_cards_and_logs() -> None:
    candidate, _, pcm_path, cards = _inputs()
    scan_roots = [cards]
    extra = Path(_required_env("SBD_M4A_PRODUCT_LOG_ROOT")).resolve()
    scan_roots.append(extra)
    pcm = pcm_path.read_bytes()
    encoded_pcm: set[str | bytes] = {
        pcm, pcm.hex(), base64.b64encode(pcm).decode(),
    }
    blobs = []
    scanned = 0
    for root in scan_roots:
        assert root.is_dir()
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            scanned += 1
            blobs.append((path.name, path.read_bytes()))
    private_paths = (
        str(cards),
        str(Path(_required_env("SBD_M4A_TARGET_CONFIG")).resolve()),
        str(Path(_required_env("SBD_M4A_INSTALL_ROOT")).resolve()),
        str(Path(tempfile.gettempdir()) / "sbd-m4a-asr"),
        str(Path(tempfile.gettempdir()) / "sbd-m4a-tts"),
    )
    hits = privacy_hits(
        blobs, (*_PRIVATE_SENTINELS, *encoded_pcm, *private_paths),
    )
    assert hits == []
    _write_card(cards, "M4A-PRIV-001", candidate, scanned_paths=scanned, hits=0)
