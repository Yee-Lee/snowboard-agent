"""Private framed-PCM worker for bounded M3 Matcha playback."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .m4a_qualification_worker import _load_tts
from .m4a_tts_quality import float_samples_to_s16le


def emit(document: dict[str, object]) -> None:
    sys.stdout.buffer.write(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    )
    sys.stdout.buffer.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--vocos", type=Path, required=True)
    args = parser.parse_args()
    tts, load_ms = _load_tts(args.model_dir, args.vocos)
    emit({"event": "READY", "load_ms": round(load_ms, 3)})
    for raw_line in sys.stdin.buffer:
        try:
            command = json.loads(raw_line)
        except json.JSONDecodeError as error:
            emit({"event": "ERROR", "code": "INVALID_JSON", "detail": str(error)})
            continue
        if command == {"op": "SHUTDOWN"}:
            emit({"event": "SHUTDOWN_ACK"})
            return 0
        if not isinstance(command, dict) or set(command) != {"op", "fixture_id", "text"}:
            emit({"event": "ERROR", "code": "INVALID_COMMAND"})
            continue
        if command["op"] != "GENERATE" or not all(
            isinstance(command[key], str) and command[key] for key in ("fixture_id", "text")
        ):
            emit({"event": "ERROR", "code": "INVALID_GENERATE"})
            continue
        generated = tts.generate(command["text"], sid=0, speed=1.0)
        if generated.sample_rate != 16_000 or not len(generated.samples):
            emit({"event": "ERROR", "code": "INVALID_PCM"})
            continue
        pcm = float_samples_to_s16le(generated.samples)
        emit({
            "event": "PCM",
            "fixture_id": command["fixture_id"],
            "sample_rate_hz": generated.sample_rate,
            "channels": 1,
            "sample_format": "S16_LE",
            "sample_count": len(generated.samples),
            "pcm_bytes": len(pcm),
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        })
        sys.stdout.buffer.write(pcm)
        sys.stdout.buffer.flush()
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
