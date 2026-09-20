"""Dependency-free I2S-speaker plus USB-microphone calibration preflight."""

from __future__ import annotations

import array
from dataclasses import dataclass
import math
import os
import re
import statistics
import subprocess
import threading
import time
from typing import Callable, Sequence


RATE_HZ = 48_000
CAPTURE_PERIOD_FRAMES = 480
CAPTURE_BLOCK_BYTES = CAPTURE_PERIOD_FRAMES * 2
PLAYBACK_PERIOD_FRAMES = 960
PULSE_HZ = 1_000
PULSE_DURATION_MS = 250
_DEVICE = re.compile(r"hw:CARD=[A-Za-z0-9_-]+,DEV=[0-9]+")
_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


class DuplexError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class CaptureBlock:
    observed_end_ns: int
    pcm_s16le: bytes

    @property
    def frames(self) -> int:
        return len(self.pcm_s16le) // 2


@dataclass(frozen=True, slots=True)
class DuplexCalibration:
    capture_rate_hz: int
    capture_channels: int
    capture_format: str
    capture_period_frames: int
    baseline_rms: float
    threshold_rms: float
    onset_rms: float
    onset_monotonic_ns: int
    maximum_clock_residual_ns: int
    detector_error_ns: int
    uncertainty_ns: int
    uncertainty_within_limit: bool
    capture_owner_stopped: bool
    playback_owner_stopped: bool


def _rms(payload: bytes) -> float:
    if not payload or len(payload) % 2:
        raise DuplexError("INVALID_CAPTURE_BLOCK")
    values = array.array("h")
    values.frombytes(payload)
    if os.sys.byteorder != "little":
        values.byteswap()
    return math.sqrt(sum(value * value for value in values) / len(values))


def analyze_capture_blocks(
    blocks: Sequence[CaptureBlock],
    *,
    baseline_blocks: int = 30,
    stable_active_blocks: int = 3,
    maximum_uncertainty_ns: int = 50_000_000,
) -> DuplexCalibration:
    if (
        baseline_blocks < 1
        or stable_active_blocks < 1
        or len(blocks) < baseline_blocks + stable_active_blocks
        or maximum_uncertainty_ns <= 0
    ):
        raise DuplexError("INSUFFICIENT_CAPTURE")
    if any(
        block.observed_end_ns <= 0
        or block.frames != CAPTURE_PERIOD_FRAMES
        for block in blocks
    ):
        raise DuplexError("INVALID_CAPTURE_BLOCK")
    if any(
        right.observed_end_ns < left.observed_end_ns
        for left, right in zip(blocks, blocks[1:])
    ):
        raise DuplexError("NON_MONOTONIC_CAPTURE")

    rms = [_rms(block.pcm_s16le) for block in blocks]
    baseline = statistics.median(rms[:baseline_blocks])
    threshold = max(300.0, baseline * 5.0)
    onset_index: int | None = None
    for index in range(baseline_blocks, len(blocks) - stable_active_blocks + 1):
        if all(value >= threshold for value in rms[index:index + stable_active_blocks]):
            onset_index = index
            break
    if onset_index is None:
        raise DuplexError("ACOUSTIC_PULSE_NOT_DETECTED")

    period_ns = CAPTURE_PERIOD_FRAMES * 1_000_000_000 // RATE_HZ
    final_end = blocks[-1].observed_end_ns
    maximum_residual = max(
        abs(
            block.observed_end_ns
            - (final_end - (len(blocks) - index - 1) * period_ns)
        )
        for index, block in enumerate(blocks)
    )
    detector_error = period_ns
    uncertainty = period_ns + maximum_residual + detector_error
    onset = blocks[onset_index].observed_end_ns - period_ns
    return DuplexCalibration(
        capture_rate_hz=RATE_HZ,
        capture_channels=1,
        capture_format="S16_LE",
        capture_period_frames=CAPTURE_PERIOD_FRAMES,
        baseline_rms=round(baseline, 3),
        threshold_rms=round(threshold, 3),
        onset_rms=round(rms[onset_index], 3),
        onset_monotonic_ns=onset,
        maximum_clock_residual_ns=maximum_residual,
        detector_error_ns=detector_error,
        uncertainty_ns=uncertainty,
        uncertainty_within_limit=uncertainty <= maximum_uncertainty_ns,
        capture_owner_stopped=True,
        playback_owner_stopped=True,
    )


def _pulse() -> bytes:
    samples = array.array("i")
    amplitude = 300_000_000
    for index in range(RATE_HZ * PULSE_DURATION_MS // 1000):
        value = int(amplitude * math.sin(2 * math.pi * PULSE_HZ * index / RATE_HZ))
        samples.extend((value, value))
    if os.sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def _require_device(value: str) -> str:
    if type(value) is not str or _DEVICE.fullmatch(value) is None:
        raise DuplexError("INVALID_ALSA_DEVICE")
    return value


def run_duplex_calibration(
    *,
    capture_device: str,
    playback_device: str,
    clock_ns: Callable[[], int] = time.monotonic_ns,
) -> DuplexCalibration:
    """Play one bounded pulse and retain no PCM or host path."""

    capture_device = _require_device(capture_device)
    playback_device = _require_device(playback_device)
    environment = {"PATH": _PATH}
    recorder = subprocess.Popen(
        [
            "arecord", "-q", "-D", capture_device, "-t", "raw",
            "-f", "S16_LE", "-c", "1", "-r", str(RATE_HZ),
            "--period-size", str(CAPTURE_PERIOD_FRAMES),
            "--buffer-size", str(CAPTURE_PERIOD_FRAMES * 4), "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
        env=environment,
    )
    if recorder.stdout is None:
        recorder.terminate()
        recorder.wait(timeout=2)
        raise DuplexError("CAPTURE_START_FAILED")
    blocks: list[CaptureBlock] = []
    reader_errors: list[BaseException] = []
    ready = threading.Event()
    stopped = threading.Event()

    def capture() -> None:
        try:
            while not stopped.is_set():
                payload = recorder.stdout.read(CAPTURE_BLOCK_BYTES)
                observed = clock_ns()
                if not payload:
                    return
                if len(payload) != CAPTURE_BLOCK_BYTES:
                    raise DuplexError("INVALID_CAPTURE_BLOCK")
                blocks.append(CaptureBlock(observed, payload))
                if len(blocks) >= 40:
                    ready.set()
        except BaseException as error:
            reader_errors.append(error)
        finally:
            ready.set()

    reader = threading.Thread(target=capture, name="m4c-usb-capture", daemon=False)
    reader.start()
    player: subprocess.Popen[bytes] | None = None
    try:
        if not ready.wait(2.0) or len(blocks) < 40 or recorder.poll() is not None:
            raise DuplexError("CAPTURE_START_FAILED")
        player = subprocess.Popen(
            [
                "aplay", "-q", "-D", playback_device, "-t", "raw",
                "-f", "S32_LE", "-c", "2", "-r", str(RATE_HZ), "-",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
        if player.stdin is None:
            raise DuplexError("PLAYBACK_START_FAILED")
        player.stdin.write(_pulse())
        player.stdin.close()
        if player.wait(timeout=3.0) != 0:
            raise DuplexError("PLAYBACK_FAILED")
        deadline = time.monotonic() + 2.0
        while len(blocks) < 120 and time.monotonic() < deadline and recorder.poll() is None:
            time.sleep(0.01)
        if len(blocks) < 70:
            raise DuplexError("INSUFFICIENT_CAPTURE")
    finally:
        stopped.set()
        if player is not None and player.poll() is None:
            player.terminate()
            try:
                player.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                player.kill()
                player.wait(timeout=1.0)
        if recorder.poll() is None:
            recorder.terminate()
        try:
            recorder.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            recorder.kill()
            recorder.wait(timeout=1.0)
        reader.join(timeout=2.0)
        recorder.stdout.close()
        if reader.is_alive():
            raise DuplexError("OWNER_CLEANUP_FAILURE")
        if reader_errors:
            raise DuplexError("CAPTURE_FAILED") from reader_errors[0]
    return analyze_capture_blocks(blocks)
