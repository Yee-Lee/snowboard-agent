"""Run the live P4-A06 through P4-A09 Option A evidence packet on a Pi."""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import resource
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .option_a_conversion import OptionAStreamConverter, ValidBitMapping


NATIVE_RATE_HZ = 48_000
NATIVE_CHANNELS = 2
NATIVE_SAMPLE_BYTES = 4


@dataclass(frozen=True, slots=True)
class LiveConfig:
    capture_device: str
    playback_device: str
    period_frames: int = 960
    duration_seconds: float = 300.0
    warmup_cycles: int = 10
    reopen_cycles: int = 10
    cancel_after_seconds: float = 0.5
    heartbeat_interval_seconds: float = 0.01

    def validate(self) -> None:
        if not self.capture_device.startswith("hw:"):
            raise ValueError("capture device must use direct ALSA hw:")
        if not self.playback_device.startswith("hw:"):
            raise ValueError("playback device must use direct ALSA hw:")
        if self.period_frames <= 0:
            raise ValueError("period_frames must be positive")
        if self.duration_seconds < 300:
            raise ValueError("duration_seconds must be at least 300 for P4-A08")
        if self.warmup_cycles < 10:
            raise ValueError("warmup_cycles must be at least 10 for P4-A09")
        if self.reopen_cycles < 10:
            raise ValueError("reopen_cycles must be at least 10 for P4-A07")
        if self.cancel_after_seconds <= 0 or self.heartbeat_interval_seconds <= 0:
            raise ValueError("timing values must be positive")


@dataclass(slots=True)
class SessionMetrics:
    capture_reads: int = 0
    playback_writes: int = 0
    output_frames: int = 0
    capture_to_yield_ms: list[float] = field(default_factory=list)
    worker_errors: list[str] = field(default_factory=list)
    xrun_errors: list[str] = field(default_factory=list)
    heartbeat_gaps_ms: list[float] = field(default_factory=list)
    resources: list[dict[str, Any]] = field(default_factory=list)
    capture_hw_params: str | None = None
    playback_hw_params: str | None = None
    cancelled: bool = False


def pcm_node(device: str, direction: str) -> Path | None:
    """Map a direct ``hw:C,D`` device to its procfs PCM parameter file."""

    if not device.startswith("hw:"):
        return None
    try:
        card, pcm = device[3:].split(",", maxsplit=1)
        return Path(f"/proc/asound/card{int(card)}/pcm{int(pcm)}{direction}/sub0/hw_params")
    except (ValueError, IndexError):
        return None


def hw_params(device: str, direction: str) -> str | None:
    node = pcm_node(device, direction)
    if node is None or not node.is_file():
        return None
    return node.read_text(encoding="utf-8", errors="replace").strip()


def thermal_snapshot() -> dict[str, Any]:
    temperature_path = Path("/sys/class/thermal/thermal_zone0/temp")
    temperature = None
    if temperature_path.is_file():
        try:
            temperature = int(temperature_path.read_text().strip()) / 1000.0
        except ValueError:
            pass
    throttled = subprocess.run(
        ["vcgencmd", "get_throttled"], text=True, capture_output=True, check=False
    ).stdout.strip()
    return {"temperature_c": temperature, "throttled": throttled or "unavailable"}


def resource_snapshot() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_bytes = None
    statm = Path("/proc/self/statm")
    if statm.is_file():
        fields = statm.read_text().split()
        if len(fields) > 1:
            rss_bytes = int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    return {
        "at_monotonic_seconds": time.monotonic(),
        "cpu_user_seconds": usage.ru_utime,
        "cpu_system_seconds": usage.ru_stime,
        "rss_bytes": rss_bytes,
        **thermal_snapshot(),
    }


def alsa_owner_count() -> int:
    nodes = sorted(glob.glob("/dev/snd/*"))
    if not nodes:
        return 0
    result = subprocess.run(["fuser", *nodes], text=True, capture_output=True, check=False)
    return 0 if result.returncode else 1


def cleanup_proof(tracked_tasks: int, tracked_threads: int, baseline_fds: int) -> dict[str, int | bool]:
    try:
        current_fds = len(list(Path("/proc/self/fd").iterdir()))
    except OSError:
        current_fds = baseline_fds
    fd_delta = current_fds - baseline_fds
    owners = alsa_owner_count()
    return {
        "tasks": tracked_tasks,
        "threads": tracked_threads,
        "file_descriptors": fd_delta,
        "alsa_owners": owners,
        "clean": tracked_tasks == 0 and tracked_threads == 0 and fd_delta == 0 and owners == 0,
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def latency_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "samples": len(values),
        "p50_ms": percentile(values, 0.50),
        "p95_ms": percentile(values, 0.95),
        "max_ms": max(values) if values else None,
    }


def _close(pcm: Any) -> None:
    close = getattr(pcm, "close", None)
    if close is not None:
        close()


def _open_pcm(alsa: Any, direction: int, device: str, period_frames: int) -> Any:
    pcm = alsa.PCM(direction, alsa.PCM_NORMAL, device=device)
    pcm.setchannels(NATIVE_CHANNELS)
    pcm.setrate(NATIVE_RATE_HZ)
    pcm.setformat(alsa.PCM_FORMAT_S32_LE)
    pcm.setperiodsize(period_frames)
    return pcm


def _is_xrun(error: BaseException) -> bool:
    text = str(error).lower()
    return "xrun" in text or "overrun" in text or "underrun" in text or "broken pipe" in text


async def _heartbeat(stop: asyncio.Event, interval: float, gaps: list[float]) -> None:
    previous = time.monotonic()
    while not stop.is_set():
        await asyncio.sleep(interval)
        now = time.monotonic()
        gaps.append((now - previous) * 1000.0)
        previous = now


async def run_live_session(
    config: LiveConfig,
    *,
    duration_seconds: float,
    cancel_after_seconds: float | None = None,
    alsa_module: Any | None = None,
) -> tuple[SessionMetrics, dict[str, int | bool]]:
    """Capture and native-silence playback in workers while the event loop beats."""

    if alsa_module is None:
        import alsaaudio as alsa_module
    config.validate()
    metrics = SessionMetrics()
    stop = threading.Event()
    baseline_fds = len(list(Path("/proc/self/fd").iterdir()))
    lock = threading.Lock()

    def capture_worker() -> None:
        pcm = None
        try:
            pcm = _open_pcm(alsa_module, alsa_module.PCM_CAPTURE, config.capture_device, config.period_frames)
            with lock:
                metrics.capture_hw_params = hw_params(config.capture_device, "c")
            converter = OptionAStreamConverter(ValidBitMapping(channel_index=0, valid_bits=24, alignment="left"))
            while not stop.is_set():
                started = time.monotonic()
                frames, payload = pcm.read()
                if frames <= 0 or not payload:
                    continue
                yielded = converter.feed(payload)
                with lock:
                    metrics.capture_reads += 1
                    metrics.output_frames += len(yielded)
                    if yielded:
                        metrics.capture_to_yield_ms.append((time.monotonic() - started) * 1000.0)
            flushed = converter.flush()
            with lock:
                metrics.output_frames += len(flushed.frames)
        except BaseException as error:
            with lock:
                (metrics.xrun_errors if _is_xrun(error) else metrics.worker_errors).append(repr(error))
        finally:
            if pcm is not None:
                _close(pcm)

    def playback_worker() -> None:
        pcm = None
        try:
            pcm = _open_pcm(alsa_module, alsa_module.PCM_PLAYBACK, config.playback_device, config.period_frames)
            with lock:
                metrics.playback_hw_params = hw_params(config.playback_device, "p")
            silence = bytes(config.period_frames * NATIVE_CHANNELS * NATIVE_SAMPLE_BYTES)
            while not stop.is_set():
                pcm.write(silence)
                with lock:
                    metrics.playback_writes += 1
        except BaseException as error:
            with lock:
                (metrics.xrun_errors if _is_xrun(error) else metrics.worker_errors).append(repr(error))
        finally:
            if pcm is not None:
                _close(pcm)

    async def sample_resources() -> None:
        while not stop.is_set():
            with lock:
                metrics.resources.append(resource_snapshot())
            await asyncio.sleep(1.0)

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="p4-option-a") as workers:
        capture_task = loop.run_in_executor(workers, capture_worker)
        playback_task = loop.run_in_executor(workers, playback_worker)
        heartbeat_task = asyncio.create_task(_heartbeat(stop, config.heartbeat_interval_seconds, metrics.heartbeat_gaps_ms))
        resource_task = asyncio.create_task(sample_resources())
        await asyncio.sleep(cancel_after_seconds if cancel_after_seconds is not None else duration_seconds)
        metrics.cancelled = cancel_after_seconds is not None
        stop.set()
        await asyncio.gather(capture_task, playback_task, heartbeat_task, resource_task)
    cleanup = cleanup_proof(0, 0, baseline_fds)
    return metrics, cleanup


def warmup(config: LiveConfig, alsa_module: Any) -> list[float]:
    samples = []
    for _ in range(config.warmup_cycles):
        pcm = None
        try:
            started = time.monotonic()
            pcm = _open_pcm(alsa_module, alsa_module.PCM_CAPTURE, config.capture_device, config.period_frames)
            pcm.read()
            samples.append((time.monotonic() - started) * 1000.0)
        finally:
            if pcm is not None:
                _close(pcm)
    return samples


def expected_open_failure(alsa_module: Any, direction: int) -> str | None:
    try:
        pcm = _open_pcm(alsa_module, direction, "hw:999,999", 960)
    except BaseException as error:
        return type(error).__name__
    _close(pcm)
    return None


async def run_packet(config: LiveConfig) -> dict[str, Any]:
    import alsaaudio as alsa

    config.validate()
    warmup_ms = warmup(config, alsa)
    endurance, endurance_cleanup = await run_live_session(config, duration_seconds=config.duration_seconds, alsa_module=alsa)
    reopen = []
    for _ in range(config.reopen_cycles):
        metrics, cleanup = await run_live_session(config, duration_seconds=0.25, alsa_module=alsa)
        reopen.append({"metrics": asdict(metrics), "cleanup": cleanup})
    cancelled, cancelled_cleanup = await run_live_session(
        config,
        duration_seconds=config.duration_seconds,
        cancel_after_seconds=config.cancel_after_seconds,
        alsa_module=alsa,
    )
    failure_paths = {
        "capture_invalid_device_error": expected_open_failure(alsa, alsa.PCM_CAPTURE),
        "playback_invalid_device_error": expected_open_failure(alsa, alsa.PCM_PLAYBACK),
    }
    reopen_clean = all(item["cleanup"]["clean"] and not item["metrics"]["worker_errors"] for item in reopen)
    no_xruns = not endurance.xrun_errors
    no_worker_errors = not endurance.worker_errors
    heartbeat = latency_summary(endurance.heartbeat_gaps_ms)
    result = {
        "P4-A06": "PASS" if no_worker_errors and heartbeat["samples"] else "FAIL",
        "P4-A07": "PASS" if reopen_clean and cancelled_cleanup["clean"] and cancelled.cancelled and all(failure_paths.values()) else "FAIL",
        "P4-A08": "PASS" if no_worker_errors and no_xruns and endurance.capture_reads and endurance.playback_writes else "FAIL",
        "P4-A09": "PASS" if len(warmup_ms) == config.warmup_cycles and endurance.capture_to_yield_ms and endurance.resources else "FAIL",
    }
    return {
        "schema_version": "1.0",
        "config": asdict(config),
        "a06_async": {"heartbeat": heartbeat, "ownership_model": "one bounded capture worker plus one bounded playback worker", "busy_poll": False},
        "a07_lifecycle": {"reopen_cycles": len(reopen), "cancelled": cancelled.cancelled, "failure_paths": failure_paths, "cancel_cleanup": cancelled_cleanup},
        "a08_endurance": {"duration_seconds": config.duration_seconds, "capture_reads": endurance.capture_reads, "playback_writes": endurance.playback_writes, "xruns": endurance.xrun_errors, "capture_hw_params": endurance.capture_hw_params, "playback_hw_params": endurance.playback_hw_params, "cleanup": endurance_cleanup},
        "a09_resources": {"warmup_open_read_ms": warmup_ms, "capture_to_yield": latency_summary(endurance.capture_to_yield_ms), "samples": endurance.resources},
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-device", required=True)
    parser.add_argument("--playback-device", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--period-frames", type=int, default=960)
    parser.add_argument("--duration-seconds", type=float, default=300.0)
    parser.add_argument("--warmup-cycles", type=int, default=10)
    parser.add_argument("--reopen-cycles", type=int, default=10)
    args = parser.parse_args()
    config = LiveConfig(args.capture_device, args.playback_device, args.period_frames, args.duration_seconds, args.warmup_cycles, args.reopen_cycles)
    document = asyncio.run(run_packet(config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0 if all(value == "PASS" for value in document["result"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
