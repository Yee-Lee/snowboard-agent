#!/usr/bin/env python3
"""Isolated Silero endpoint supervisor for one persistent whisper.cpp worker."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import os
import select
import signal
import struct
import subprocess
import sys
import time
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any


MAX_CONTROL_BYTES = 16 * 1024
FRAME_BYTES = 640
SAMPLE_RATE = 16000
MAX_FRAMES = 3000
PRE_SPEECH_FRAMES = 25
PROMPT = "繁體中文。常用技術詞彙：Wi-Fi、audio frame、音訊基線、候選語音模型、離線執行。"
PROMPT_SHA256 = "e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef"
VAD_RUNTIME_DISTRIBUTIONS = {
    "onnxruntime": "1.29.0",
    "numpy": "2.5.2",
    "flatbuffers": "25.12.19",
    "packaging": "26.3",
    "protobuf": "7.36.0",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_runtime_identity() -> None:
    try:
        actual = {
            name: importlib.metadata.version(name)
            for name in VAD_RUNTIME_DISTRIBUTIONS
        }
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError("VAD_RUNTIME_IDENTITY") from error
    if actual != VAD_RUNTIME_DISTRIBUTIONS:
        raise RuntimeError("VAD_RUNTIME_IDENTITY")


def emit(value: dict[str, Any]) -> None:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_CONTROL_BYTES:
        raise RuntimeError("CONTROL_BOUND")
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def read_control() -> dict[str, Any] | None:
    raw = sys.stdin.buffer.readline(MAX_CONTROL_BYTES + 1)
    if raw == b"":
        return None
    if len(raw) > MAX_CONTROL_BYTES or not raw.endswith(b"\n"):
        raise RuntimeError("CONTROL_BOUND")
    try:
        value = json.loads(raw[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("CONTROL_JSON") from error
    if not isinstance(value, dict) or value.get("protocol") != 1:
        raise RuntimeError("CONTROL_SCHEMA")
    return value


def read_exact(count: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < count:
        block = sys.stdin.buffer.read(count - len(chunks))
        if not block:
            raise RuntimeError("PAYLOAD_EOF")
        chunks.extend(block)
    return bytes(chunks)


class EndpointDetector:
    """Request-local fixed Silero hysteresis and padding state."""

    def __init__(self) -> None:
        self.speech_start_ms: int | None = None
        self.possible_end_ms: int | None = None
        self.speech_end_ms: int | None = None
        self.triggered = False

    def observe(self, probability: float, window_start_ms: int) -> None:
        if probability >= 0.5:
            self.possible_end_ms = None
            if not self.triggered:
                self.speech_start_ms = window_start_ms
                self.triggered = True
            return
        if self.triggered and probability < 0.35:
            if self.possible_end_ms is None:
                self.possible_end_ms = window_start_ms
            if window_start_ms - self.possible_end_ms >= 500:
                assert self.speech_start_ms is not None
                if self.possible_end_ms - self.speech_start_ms >= 250:
                    self.speech_end_ms = self.possible_end_ms
                else:
                    self.speech_start_ms = None
                    self.possible_end_ms = None
                    self.triggered = False

    def endpoint(self, captured_ms: int) -> bool:
        return self.speech_end_ms is not None and captured_ms - self.speech_end_ms >= 600

    def bounds(self, captured_ms: int) -> tuple[int, int]:
        if self.speech_start_ms is None or self.speech_end_ms is None:
            raise RuntimeError("ENDPOINT_NOT_READY")
        return max(0, self.speech_start_ms - 500), min(captured_ms, self.speech_end_ms + 600)


class StreamingEndpoint:
    """20 ms frame intake with a fixed 160 ms mask and 512-sample VAD windows."""

    def __init__(self, probability: Callable[[bytes], float]) -> None:
        self._probability = probability
        self.detector = EndpointDetector()
        self.pcm = bytearray()
        self._pending = bytearray()
        self._next_window_start_ms = 160
        self._captured_frames = 0
        self._pcm_start_frame = 0
        self._speech_buffer_start_frame: int | None = None

    @property
    def captured_frames(self) -> int:
        return self._captured_frames

    @property
    def retained_frames(self) -> int:
        """Number of request frames currently retained in the bounded buffer."""
        return len(self.pcm) // FRAME_BYTES

    def add_frame(self, frame: bytes) -> bool:
        if len(frame) != FRAME_BYTES:
            raise ValueError("frame must contain exactly 640 bytes")
        self.pcm.extend(frame)
        self._captured_frames += 1
        if self._captured_frames > MAX_FRAMES:
            raise OverflowError("request exceeds bounded capture")
        if self.captured_frames > 8:
            self._pending.extend(frame)
            while len(self._pending) >= 1024:
                window = bytes(self._pending[:1024])
                del self._pending[:1024]
                was_triggered = self.detector.triggered
                self.detector.observe(self._probability(window), self._next_window_start_ms)
                if not was_triggered and self.detector.triggered:
                    # The triggering frame follows exactly 25 retained 20 ms
                    # pre-speech frames.  Capture the absolute start so the
                    # request can no longer grow at its silent front edge.
                    self._speech_buffer_start_frame = max(
                        0, self._captured_frames - PRE_SPEECH_FRAMES - 1,
                    )
                elif was_triggered and not self.detector.triggered:
                    self._speech_buffer_start_frame = None
                self._next_window_start_ms += 32
        if not self.detector.triggered:
            excess = self.retained_frames - PRE_SPEECH_FRAMES
            if excess > 0:
                del self.pcm[:excess * FRAME_BYTES]
                self._pcm_start_frame += excess
        return self.detector.endpoint(self.captured_frames * 20)

    def bounded_pcm(self) -> bytes:
        self.detector.bounds(self.captured_frames * 20)
        if self._speech_buffer_start_frame is None:
            raise RuntimeError("ENDPOINT_NOT_READY")
        start = (
            self._speech_buffer_start_frame - self._pcm_start_frame
        ) * FRAME_BYTES
        if start < 0:
            raise RuntimeError("PRE_SPEECH_BUFFER_UNDERRUN")
        # Endpoint is evaluated only after a complete 20 ms frame.  Retaining
        # through that frame makes the emitted bounded PCM a verifiable suffix
        # of the parent capture while providing at least the fixed 600 ms pad.
        return bytes(self.pcm[start:])


class Silero:
    def __init__(self, model: Path) -> None:
        require_runtime_identity()
        import numpy as np
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
        if [item.name for item in self._session.get_inputs()] != ["input", "state", "sr"]:
            raise RuntimeError("VAD_INPUT_SCHEMA")
        self._np = np
        self.reset()

    def reset(self) -> None:
        self._state = self._np.zeros((2, 1, 128), dtype=self._np.float32)
        self._context = self._np.zeros((1, 64), dtype=self._np.float32)

    def probability(self, window: bytes) -> float:
        samples = self._np.frombuffer(window, dtype="<i2").astype(self._np.float32) / 32768.0
        model_input = self._np.concatenate((self._context, samples.reshape(1, -1)), axis=1)
        output, self._state = self._session.run(None, {
            "input": model_input, "state": self._state,
            "sr": self._np.array(16000, dtype=self._np.int64),
        })
        self._context = model_input[:, -64:]
        return float(output.reshape(-1)[0])


class NativeWorker:
    def __init__(self, binary: Path, model: Path, work_dir: Path) -> None:
        self._stderr = (work_dir / "native.stderr").open("xb")
        self._process = subprocess.Popen(
            [str(binary), "--model", str(model), "--threads", "4", "--decoder", "greedy", "--initial-prompt", PROMPT],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
            cwd=work_dir, start_new_session=False, bufsize=0,
        )
        ready = self._line(300.0).split("\t")
        if len(ready) != 4 or ready[:2] != ["READY", "1.9.2"] or int(ready[3]) != self._process.pid:
            self.terminate()
            raise RuntimeError("NATIVE_READY")

    @property
    def pid(self) -> int:
        return self._process.pid

    def _line(self, timeout: float) -> str:
        assert self._process.stdout is not None
        readable, _, _ = select.select([self._process.stdout], [], [], timeout)
        if not readable:
            raise TimeoutError("NATIVE_TIMEOUT")
        raw = self._process.stdout.readline(1024 * 1024 + 1)
        if not raw or len(raw) > 1024 * 1024:
            raise RuntimeError("NATIVE_PROTOCOL")
        return raw.rstrip(b"\n").decode("ascii")

    def transcribe(self, wav_path: Path) -> tuple[str, float]:
        assert self._process.stdin is not None
        self._process.stdin.write(f"TRANSCRIBE\t{wav_path}\n".encode("utf-8"))
        self._process.stdin.flush()
        started = time.monotonic()
        fields = self._line(120.0).split("\t")
        if len(fields) == 2 and fields[0] == "ERROR":
            raise RuntimeError("INFERENCE_REJECTED")
        if len(fields) != 5 or fields[0] != "RESULT":
            raise RuntimeError("NATIVE_RESULT")
        return bytes.fromhex(fields[1]).decode("utf-8"), (time.monotonic() - started) * 1000

    def stop(self) -> None:
        if self._process.poll() is None:
            assert self._process.stdin is not None
            self._process.stdin.write(b"QUIT\n")
            self._process.stdin.flush()
            if self._line(5.0) != "BYE":
                self.terminate()
                raise RuntimeError("NATIVE_SHUTDOWN")
            self._process.wait(timeout=5.0)
        self._close()

    def terminate(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2.0)
        self._close()

    def _close(self) -> None:
        if self._process.stdin:
            self._process.stdin.close()
        if self._process.stdout:
            self._process.stdout.close()
        self._stderr.close()


def write_wav(path: Path, pcm: bytes) -> None:
    with path.open("xb") as raw:
        with wave.open(raw, "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(16000)
            target.writeframes(pcm)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vad-model", type=Path, required=True)
    parser.add_argument("--asr-binary", type=Path, required=True)
    parser.add_argument("--asr-model", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.getpid() != os.getpgrp() or args.work_dir.resolve() != Path.cwd().resolve():
        raise RuntimeError("PROCESS_OWNERSHIP")
    if hashlib.sha256(PROMPT.encode("utf-8")).hexdigest() != PROMPT_SHA256:
        raise RuntimeError("PROMPT_IDENTITY")
    vad = Silero(args.vad_model)
    native = NativeWorker(args.asr_binary, args.asr_model, args.work_dir)
    if os.getpgid(native.pid) != os.getpgrp():
        native.terminate()
        raise RuntimeError("NESTED_PROCESS_GROUP")
    emit({
        "protocol": 1, "event": "READY", "pid": os.getpid(), "pgid": os.getpgrp(),
        "runtime_lock_sha256": sha256_file(args.runtime_lock),
        "vad_model_sha256": sha256_file(args.vad_model),
        "asr_binary_sha256": sha256_file(args.asr_binary),
        "asr_model_sha256": sha256_file(args.asr_model),
        "profile_sha256": args.profile_sha256,
    })
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")
    future: concurrent.futures.Future[tuple[str, float]] | None = None
    stream: StreamingEndpoint | None = None
    active_id: int | None = None
    sequence = 0
    cancelled = False
    wav_path: Path | None = None
    last_id = 0
    try:
        while True:
            if future is not None and future.done():
                request_id = active_id
                assert request_id is not None
                try:
                    transcript, latency_ms = future.result()
                    if cancelled:
                        emit({"protocol": 1, "event": "CANCELLED", "request_id": request_id})
                    else:
                        emit({"protocol": 1, "event": "RESULT", "request_id": request_id, "text": transcript, "language": "zh-TW", "latency_ms": round(latency_ms, 3)})
                except BaseException:
                    emit({"protocol": 1, "event": "ERROR", "request_id": request_id, "code": "INFERENCE_REJECTED"})
                if wav_path is not None:
                    wav_path.unlink(missing_ok=True)
                future = None
                stream = None
                active_id = None
                cancelled = False
                wav_path = None
                continue
            readable, _, _ = select.select([sys.stdin.buffer], [], [], 0.05 if future is not None else None)
            if not readable:
                continue
            command = read_control()
            if command is None:
                return 3
            op = command.get("op")
            if op == "SHUTDOWN":
                if set(command) != {"protocol", "op"} or active_id is not None:
                    return 3
                native.stop()
                emit({"protocol": 1, "event": "SHUTDOWN_ACK"})
                return 0
            if op == "BEGIN":
                required = {"protocol", "op", "request_id", "format", "frame_bytes"}
                if set(command) != required:
                    return 3
                request_id = command["request_id"]
                if type(request_id) is not int or request_id <= last_id:
                    return 3
                if active_id is not None:
                    last_id = request_id
                    emit({"protocol": 1, "event": "BUSY", "request_id": request_id})
                    continue
                if command["format"] != "16000_mono_s16le" or command["frame_bytes"] != FRAME_BYTES:
                    emit({"protocol": 1, "event": "ERROR", "request_id": request_id, "code": "INVALID_FRAME"})
                    last_id = request_id
                    continue
                last_id = request_id
                active_id = request_id
                stream = StreamingEndpoint(vad.probability)
                vad.reset()
                sequence = 0
                continue
            if op == "FRAME":
                required = {"protocol", "op", "request_id", "sequence", "payload_bytes"}
                if set(command) != required or command.get("request_id") != active_id or command.get("sequence") != sequence or command.get("payload_bytes") != FRAME_BYTES or future is not None:
                    return 3
                frame = read_exact(FRAME_BYTES)
                assert stream is not None
                try:
                    endpoint = stream.add_frame(frame)
                except OverflowError:
                    emit({"protocol": 1, "event": "ERROR", "request_id": active_id, "code": "NO_SPEECH"})
                    active_id = None
                    stream = None
                    continue
                captured_frames = stream.captured_frames
                assert active_id is not None
                if endpoint:
                    bounded = stream.bounded_pcm()
                    wav_path = args.work_dir / f"request-{active_id}.wav"
                    write_wav(wav_path, bounded)
                    emit({
                        "protocol": 1, "event": "ENDPOINT", "request_id": active_id,
                        "captured_frames": captured_frames, "bounded_samples": len(bounded) // 2,
                        "bounded_pcm_sha256": hashlib.sha256(bounded).hexdigest(),
                    })
                    future = executor.submit(native.transcribe, wav_path)
                else:
                    emit({"protocol": 1, "event": "FRAME_ACCEPTED", "request_id": active_id, "sequence": sequence})
                sequence += 1
                continue
            if op == "CANCEL":
                if set(command) != {"protocol", "op", "request_id"} or command.get("request_id") != active_id:
                    return 3
                if future is not None:
                    cancelled = True
                    emit({"protocol": 1, "event": "CANCEL_DEFERRED", "request_id": active_id})
                else:
                    request_id = active_id
                    active_id = None
                    stream = None
                    emit({"protocol": 1, "event": "CANCELLED", "request_id": request_id})
                continue
            return 3
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        if wav_path is not None:
            wav_path.unlink(missing_ok=True)
        native.terminate()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        print(json.dumps({"stage": "supervisor", "code": type(error).__name__}, separators=(",", ":")), file=sys.stderr)
        raise
