"""Deterministic framed-PCM peer used only by M3 unit tests."""

from __future__ import annotations

import hashlib
import json
import sys


def emit(document):
    sys.stdout.buffer.write(json.dumps(document).encode() + b"\n")
    sys.stdout.buffer.flush()


def main() -> int:
    emit({"event": "READY", "load_ms": 0})
    for line in sys.stdin.buffer:
        command = json.loads(line)
        if command == {"op": "SHUTDOWN"}:
            emit({"event": "SHUTDOWN_ACK"})
            return 0
        pcm = bytes.fromhex("00000100ff7f0080")
        emit({
            "event": "PCM",
            "fixture_id": command["fixture_id"],
            "sample_rate_hz": 16000,
            "channels": 1,
            "sample_format": "S16_LE",
            "sample_count": 4,
            "pcm_bytes": len(pcm),
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        })
        sys.stdout.buffer.write(pcm)
        sys.stdout.buffer.flush()
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
