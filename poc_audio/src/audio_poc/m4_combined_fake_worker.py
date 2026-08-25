"""Persistent fake domain worker for local-only M4 combined validation."""

from __future__ import annotations

import argparse
import json
import sys


def _emit(event: str, **fields: object) -> None:
    print(json.dumps({"protocol": 1, "event": event, **fields}, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, choices=("vad", "asr", "tts"))
    args = parser.parse_args()
    _emit("ready", domain=args.domain)
    for line in sys.stdin:
        try:
            command = json.loads(line)
        except json.JSONDecodeError:
            _emit("error", code="INVALID_JSON")
            continue
        if not isinstance(command, dict):
            _emit("error", code="INVALID_COMMAND")
            continue
        if command.get("command") == "run" and isinstance(command.get("session_id"), str):
            _emit("result", domain=args.domain, session_id=command["session_id"])
        elif command == {"command": "shutdown"}:
            _emit("shutdown_ack", domain=args.domain)
            return 0
        else:
            _emit("error", code="INVALID_COMMAND")
    _emit("error", code="STDIN_CLOSED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
