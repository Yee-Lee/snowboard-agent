#!/usr/bin/env python3
"""Isolated persistent sherpa/Matcha Audio Protocol v1 child."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import os
import select
import struct
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any


# sherpa-onnx embeds ONNX Runtime.  Disable its 1DS uploader before any direct
# or indirect native-engine initialization, including diagnostic invocation.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"


MAX_CONTROL_BYTES = 16 * 1024
MAX_PCM_BYTES = 64 * 1024 * 1024
VOICE_ID = "matcha-zh-en-default-sid-0"
TTS_RUNTIME_DISTRIBUTIONS = {
    "sherpa-onnx": "1.13.5",
    "sherpa-onnx-core": "1.13.5",
    "numpy": "2.5.2",
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
            for name in TTS_RUNTIME_DISTRIBUTIONS
        }
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError("TTS_RUNTIME_IDENTITY") from error
    if actual != TTS_RUNTIME_DISTRIBUTIONS:
        raise RuntimeError("TTS_RUNTIME_IDENTITY")


def float_samples_to_s16le(samples: Iterable[float]) -> bytes:
    values = []
    for sample in samples:
        value = float(sample)
        if value <= -1.0:
            values.append(-32768)
        elif value >= 1.0:
            values.append(32767)
        else:
            values.append(round(value * 32767))
    return struct.pack(f"<{len(values)}h", *values)


def emit(value: dict[str, Any], payload: bytes | None = None) -> None:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_CONTROL_BYTES:
        raise RuntimeError("CONTROL_BOUND")
    sys.stdout.buffer.write(encoded)
    if payload is not None:
        sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def read_control() -> dict[str, Any] | None:
    # Keep select() and reads on the same unbuffered fd model.  A buffered
    # readline may otherwise hide a coalesced CANCEL/GENERATE from select().
    stream = getattr(sys.stdin.buffer, "raw", sys.stdin.buffer)
    raw = stream.readline(MAX_CONTROL_BYTES + 1)
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


def load_tts(model_dir: Path, vocoder: Path):
    require_runtime_identity()
    import sherpa_onnx

    rule_fsts = ",".join(str(model_dir / name) for name in ("phone-zh.fst", "date-zh.fst", "number-zh.fst"))
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=str(model_dir / "model-steps-3.onnx"),
                vocoder=str(vocoder),
                lexicon=str(model_dir / "lexicon.txt"),
                tokens=str(model_dir / "tokens.txt"),
                data_dir=str(model_dir / "espeak-ng-data"),
            ),
            provider="cpu",
            num_threads=2,
        ),
        rule_fsts=rule_fsts,
        max_num_sentences=1,
    )
    if not config.validate():
        raise RuntimeError("MATCHA_CONFIG")
    return sherpa_onnx.OfflineTts(config)


def synthesize(engine, text: str) -> tuple[bytes, float]:
    started = time.monotonic()
    audio = engine.generate(text, sid=0, speed=1.0)
    latency_ms = (time.monotonic() - started) * 1000
    if audio.sample_rate != 16000 or not len(audio.samples):
        raise RuntimeError("INVALID_PCM")
    pcm = float_samples_to_s16le(audio.samples)
    if not pcm or len(pcm) > MAX_PCM_BYTES or len(pcm) % 2:
        raise RuntimeError("INVALID_PCM")
    return pcm, latency_ms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--vocoder", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.getpid() != os.getpgrp() or args.work_dir.resolve() != Path.cwd().resolve():
        raise RuntimeError("PROCESS_OWNERSHIP")
    for name in ("model-steps-3.onnx", "lexicon.txt", "tokens.txt", "espeak-ng-data"):
        if not (args.model_dir / name).exists():
            raise RuntimeError("MODEL_CLOSURE")
    engine = load_tts(args.model_dir, args.vocoder)
    emit({
        "protocol": 1, "event": "READY", "pid": os.getpid(), "pgid": os.getpgrp(),
        "runtime_lock_sha256": sha256_file(args.runtime_lock),
        "acoustic_model_sha256": sha256_file(args.model_dir / "model-steps-3.onnx"),
        "vocoder_sha256": sha256_file(args.vocoder), "profile_sha256": args.profile_sha256,
    })
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="matcha")
    future: concurrent.futures.Future[tuple[bytes, float]] | None = None
    active_id: int | None = None
    cancelled = False
    last_id = 0
    try:
        while True:
            if future is not None and future.done():
                request_id = active_id
                assert request_id is not None
                try:
                    pcm, _latency_ms = future.result()
                    if cancelled:
                        emit({"protocol": 1, "event": "CANCELLED", "request_id": request_id})
                    else:
                        emit({
                            "protocol": 1, "event": "PCM", "request_id": request_id,
                            "sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE",
                            "sample_count": len(pcm) // 2, "payload_bytes": len(pcm),
                            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
                        }, pcm)
                except BaseException:
                    emit({"protocol": 1, "event": "ERROR", "request_id": request_id, "code": "GENERATION_REJECTED"})
                future = None
                active_id = None
                cancelled = False
                continue
            readable, _, _ = select.select([sys.stdin.buffer], [], [], 0.05 if future is not None else None)
            if not readable:
                continue
            command = read_control()
            if command is None:
                return 3
            op = command.get("op")
            if op == "SHUTDOWN":
                if set(command) != {"protocol", "op"} or future is not None:
                    return 3
                emit({"protocol": 1, "event": "SHUTDOWN_ACK"})
                return 0
            if op == "GENERATE":
                if set(command) != {"protocol", "op", "request_id", "text", "voice_id"}:
                    return 3
                request_id = command["request_id"]
                if type(request_id) is not int or request_id <= last_id:
                    return 3
                if future is not None:
                    last_id = request_id
                    emit({"protocol": 1, "event": "BUSY", "request_id": request_id})
                    continue
                text = command["text"]
                if type(text) is not str or not text or "\x00" in text or command["voice_id"] != VOICE_ID:
                    emit({"protocol": 1, "event": "ERROR", "request_id": request_id, "code": "INVALID_TEXT"})
                    last_id = request_id
                    continue
                last_id = request_id
                active_id = request_id
                future = executor.submit(synthesize, engine, text)
                continue
            if op == "CANCEL":
                if set(command) != {"protocol", "op", "request_id"} or future is None or command["request_id"] != active_id:
                    return 3
                cancelled = True
                emit({"protocol": 1, "event": "CANCEL_DEFERRED", "request_id": active_id})
                continue
            return 3
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        print(json.dumps({"stage": "worker", "code": type(error).__name__}, separators=(",", ":")), file=sys.stderr)
        raise
