"""Persistent Matcha child protocol used by the M2 lifecycle packet."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

from .m4a_qualification_worker import _load_tts, _tts_once


def emit(event: str, **fields: Any) -> None:
    print(json.dumps({"protocol": 1, "event": event, **fields}, sort_keys=True), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--vocos", type=Path, required=True)
    parser.add_argument("--ignore-term", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.ignore_term:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    tts, load_ms = _load_tts(args.model_dir, args.vocos)
    emit("ready", load_ms=round(load_ms, 3))
    for line in sys.stdin:
        message = json.loads(line)
        command = message.get("command")
        session_id = str(message.get("session_id", ""))
        if command == "shutdown":
            emit("stopped", session_id=session_id)
            return 0
        if command != "run":
            emit("error", session_id=session_id, code="INVALID_COMMAND")
            continue
        mode = str(message.get("mode", "success"))
        emit("started", session_id=session_id)
        if mode == "declared_error":
            emit("error", session_id=session_id, code="DECLARED_INPUT_ERROR")
            continue
        result = _tts_once(
            tts,
            {
                "fixture_id": str(message.get("fixture_id", "tts-001")),
                "category": "lifecycle",
                "text": str(message.get("text", "")),
            },
        )
        safe = {
            name: result[name]
            for name in (
                "fixture_id", "latency_ms", "sample_rate_hz", "sample_count",
                "channels", "audio_duration_seconds", "rtf", "pcm_emitted",
                "audio_device_opened",
            )
        }
        if mode == "generate_then_wait":
            emit("generated", session_id=session_id, result=safe)
            while True:
                time.sleep(1)
        emit("result", session_id=session_id, result=safe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
