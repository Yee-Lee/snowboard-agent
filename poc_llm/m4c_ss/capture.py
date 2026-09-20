"""Bounded USB microphone capture for private M4C acoustic samples."""

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

from poc_llm.m4c_ss.duplex import (
    CAPTURE_BLOCK_BYTES, CAPTURE_PERIOD_FRAMES, RATE_HZ, CaptureBlock,
)


_DEVICE = re.compile(r"hw:CARD=[A-Za-z0-9_-]+,DEV=[0-9]+")
_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


class CaptureError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class CaptureRecording:
    blocks: tuple[CaptureBlock, ...]
    pcm_s16le: bytes
    owner_stopped: bool


@dataclass(frozen=True, slots=True)
class AcousticActivity:
    baseline_rms: float
    threshold_rms: float
    onset_monotonic_ns: int
    final_monotonic_ns: int
    maximum_clock_residual_ns: int
    detector_error_ns: int
    uncertainty_ns: int


def _rms(payload: bytes) -> float:
    if not payload or len(payload) % 2:
        raise CaptureError("INVALID_CAPTURE_BLOCK")
    values = array.array("h")
    values.frombytes(payload)
    if os.sys.byteorder != "little":
        values.byteswap()
    return math.sqrt(sum(value * value for value in values) / len(values))


def analyze_acoustic_activity(
    blocks: Sequence[CaptureBlock],
    *,
    baseline_blocks: int = 30,
    stable_active_blocks: int = 3,
    not_before_ns: int | None = None,
) -> AcousticActivity:
    if (
        baseline_blocks < 1
        or stable_active_blocks < 1
        or len(blocks) < baseline_blocks + stable_active_blocks
    ):
        raise CaptureError("INSUFFICIENT_CAPTURE")
    if (
        not_before_ns is not None
        and (type(not_before_ns) is not int or not_before_ns < 0)
    ):
        raise CaptureError("INVALID_ONSET_BOUND")
    if any(block.frames != CAPTURE_PERIOD_FRAMES for block in blocks):
        raise CaptureError("INVALID_CAPTURE_BLOCK")
    if any(
        right.observed_end_ns < left.observed_end_ns
        for left, right in zip(blocks, blocks[1:])
    ):
        raise CaptureError("NON_MONOTONIC_CAPTURE")
    rms = [_rms(block.pcm_s16le) for block in blocks]
    baseline = statistics.median(rms[:baseline_blocks])
    threshold = max(300.0, baseline * 5.0)
    active = [value >= threshold for value in rms]
    period_ns = CAPTURE_PERIOD_FRAMES * 1_000_000_000 // RATE_HZ
    search_start = baseline_blocks
    if not_before_ns is not None:
        search_start = max(search_start, next(
            (index for index, block in enumerate(blocks)
             if block.observed_end_ns - period_ns >= not_before_ns),
            len(blocks),
        ))
    starts = [
        index for index in range(search_start, len(active) - stable_active_blocks + 1)
        if all(active[index:index + stable_active_blocks])
    ]
    if not starts:
        raise CaptureError("ACOUSTIC_ACTIVITY_NOT_DETECTED")
    onset_index = starts[0]
    final_index = starts[-1] + stable_active_blocks - 1
    final_observed = blocks[-1].observed_end_ns
    maximum_residual = max(
        abs(
            block.observed_end_ns
            - (final_observed - (len(blocks) - index - 1) * period_ns)
        )
        for index, block in enumerate(blocks)
    )
    detector_error = period_ns
    return AcousticActivity(
        baseline_rms=round(baseline, 3),
        threshold_rms=round(threshold, 3),
        onset_monotonic_ns=blocks[onset_index].observed_end_ns - period_ns,
        final_monotonic_ns=blocks[final_index].observed_end_ns,
        maximum_clock_residual_ns=maximum_residual,
        detector_error_ns=detector_error,
        uncertainty_ns=period_ns + maximum_residual + detector_error,
    )


class UsbCaptureSession:
    """Own one dependency-free arecord process and non-daemon reader."""

    def __init__(
        self,
        device: str,
        *,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if type(device) is not str or _DEVICE.fullmatch(device) is None:
            raise CaptureError("INVALID_ALSA_DEVICE")
        self.device = device
        self.clock_ns = clock_ns
        self._process: subprocess.Popen[bytes] | None = None
        self._reader: threading.Thread | None = None
        self._blocks: list[CaptureBlock] = []
        self._errors: list[BaseException] = []
        self._ready = threading.Event()
        self._stopping = threading.Event()

    def start(self, *, minimum_baseline_blocks: int = 30, timeout_s: float = 2.0) -> None:
        if self._process is not None or minimum_baseline_blocks < 1 or timeout_s <= 0:
            raise CaptureError("CAPTURE_START_INVALID")
        process = subprocess.Popen(
            [
                "arecord", "-q", "-D", self.device, "-t", "raw",
                "-f", "S16_LE", "-c", "1", "-r", str(RATE_HZ),
                "--period-size", str(CAPTURE_PERIOD_FRAMES),
                "--buffer-size", str(CAPTURE_PERIOD_FRAMES * 4), "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            env={"PATH": _PATH},
        )
        if process.stdout is None:
            process.terminate()
            process.wait(timeout=2)
            raise CaptureError("CAPTURE_START_FAILED")
        self._process = process

        def read_blocks() -> None:
            try:
                while True:
                    payload = process.stdout.read(CAPTURE_BLOCK_BYTES)
                    observed = self.clock_ns()
                    if not payload:
                        return
                    if len(payload) != CAPTURE_BLOCK_BYTES:
                        if self._stopping.is_set():
                            return
                        raise CaptureError("INVALID_CAPTURE_BLOCK")
                    self._blocks.append(CaptureBlock(observed, payload))
                    if len(self._blocks) >= minimum_baseline_blocks:
                        self._ready.set()
            except BaseException as error:
                self._errors.append(error)
            finally:
                self._ready.set()

        self._reader = threading.Thread(
            target=read_blocks, name="m4c-usb-capture", daemon=False,
        )
        self._reader.start()
        if (
            not self._ready.wait(timeout_s)
            or len(self._blocks) < minimum_baseline_blocks
            or process.poll() is not None
        ):
            self.stop()
            raise CaptureError("CAPTURE_START_FAILED")

    def stop(self) -> CaptureRecording:
        process, reader = self._process, self._reader
        if process is None or reader is None:
            raise CaptureError("CAPTURE_NOT_STARTED")
        self._stopping.set()
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)
        reader.join(timeout=2.0)
        if process.stdout is not None:
            process.stdout.close()
        self._process = None
        self._reader = None
        if reader.is_alive() or self._errors:
            raise CaptureError("CAPTURE_CLEANUP_FAILED")
        blocks = tuple(self._blocks)
        return CaptureRecording(
            blocks=blocks,
            pcm_s16le=b"".join(block.pcm_s16le for block in blocks),
            owner_stopped=True,
        )


class AlsaTimestampCaptureSession:
    """Capture blocks using ALSA monotonic hardware-position timestamps."""

    def __init__(
        self,
        device: str,
        *,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if type(device) is not str or _DEVICE.fullmatch(device) is None:
            raise CaptureError("INVALID_ALSA_DEVICE")
        self.device = device
        self.clock_ns = clock_ns
        self._reader: threading.Thread | None = None
        self._blocks: list[CaptureBlock] = []
        self._errors: list[BaseException] = []
        self._ready = threading.Event()
        self._stopping = threading.Event()

    def start(self, *, minimum_baseline_blocks: int = 30, timeout_s: float = 2.0) -> None:
        if self._reader is not None or minimum_baseline_blocks < 1 or timeout_s <= 0:
            raise CaptureError("CAPTURE_START_INVALID")

        def read_blocks() -> None:
            pcm = None
            try:
                import alsaaudio

                pcm = alsaaudio.PCM(
                    type=alsaaudio.PCM_CAPTURE,
                    mode=alsaaudio.PCM_NORMAL,
                    device=self.device,
                )
                pcm.setchannels(1)
                pcm.setrate(RATE_HZ)
                pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
                pcm.setperiodsize(CAPTURE_PERIOD_FRAMES)
                if hasattr(pcm, "setperiods"):
                    pcm.setperiods(4)
                pcm.set_tstamp_mode(alsaaudio.PCM_TSTAMP_ENABLE)
                pcm.set_tstamp_type(alsaaudio.PCM_TSTAMP_TYPE_MONOTONIC)
                info = pcm.info()
                actual = (
                    info.get("rate"), info.get("channels"),
                    str(info.get("format_name", "")).upper(), info.get("period_size"),
                )
                if actual != (RATE_HZ, 1, "S16_LE", CAPTURE_PERIOD_FRAMES):
                    raise CaptureError("CAPTURE_NEGOTIATION_MISMATCH")
                while not self._stopping.is_set():
                    frames, payload = pcm.read()
                    seconds, nanoseconds, available = pcm.htimestamp()
                    if frames == 0:
                        continue
                    if (
                        frames != CAPTURE_PERIOD_FRAMES
                        or type(payload) is not bytes
                        or len(payload) != CAPTURE_BLOCK_BYTES
                        or type(seconds) is not int
                        or type(nanoseconds) is not int
                        or type(available) is not int
                        or available < 0
                    ):
                        raise CaptureError("INVALID_CAPTURE_BLOCK")
                    hardware_ns = seconds * 1_000_000_000 + nanoseconds
                    if abs(hardware_ns - self.clock_ns()) > 1_000_000_000:
                        raise CaptureError("CAPTURE_CLOCK_MISMATCH")
                    observed_end_ns = hardware_ns - available * 1_000_000_000 // RATE_HZ
                    self._blocks.append(CaptureBlock(observed_end_ns, payload))
                    if len(self._blocks) >= minimum_baseline_blocks:
                        self._ready.set()
            except BaseException as error:
                self._errors.append(error)
            finally:
                if pcm is not None:
                    pcm.close()
                self._ready.set()

        self._reader = threading.Thread(
            target=read_blocks, name="m4c-usb-hwtime-capture", daemon=False,
        )
        self._reader.start()
        if (
            not self._ready.wait(timeout_s)
            or len(self._blocks) < minimum_baseline_blocks
            or self._errors
        ):
            self._stopping.set()
            self._reader.join(timeout=2.0)
            self._reader = None
            if self._errors:
                raise CaptureError("CAPTURE_START_FAILED") from self._errors[0]
            raise CaptureError("CAPTURE_START_FAILED")

    def stop(self) -> CaptureRecording:
        reader = self._reader
        if reader is None:
            raise CaptureError("CAPTURE_NOT_STARTED")
        self._stopping.set()
        reader.join(timeout=2.0)
        self._reader = None
        if reader.is_alive() or self._errors:
            raise CaptureError("CAPTURE_CLEANUP_FAILED")
        blocks = tuple(self._blocks)
        return CaptureRecording(
            blocks=blocks,
            pcm_s16le=b"".join(block.pcm_s16le for block in blocks),
            owner_stopped=True,
        )
