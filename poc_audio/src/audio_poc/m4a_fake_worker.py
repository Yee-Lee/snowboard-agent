"""Fake-only worker implementing the M4a candidate lifecycle protocol."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time


def emit(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, "protocol": 1, **fields}, sort_keys=True), flush=True)


def command() -> dict[str, object]:
    line = sys.stdin.readline()
    if not line:
        raise SystemExit(2)
    message = json.loads(line)
    if not isinstance(message, dict):
        raise SystemExit(2)
    return message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("success", "error", "cancelable", "hang", "stubborn"))
    args = parser.parse_args()
    if args.mode == "stubborn":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

    emit("ready")
    start = command()
    if start.get("command") != "start" or not isinstance(start.get("session_id"), str):
        emit("error", code="PROTOCOL_START_REQUIRED")
        return 2
    emit("started", session_id=start["session_id"])
    action = command()
    if action.get("command") == "cancel":
        emit("cancelled", session_id=start["session_id"])
        return 0
    if action.get("command") != "run":
        emit("error", code="PROTOCOL_RUN_REQUIRED")
        return 2
    if args.mode == "success":
        emit("result", session_id=start["session_id"], value="deterministic")
        return 0
    if args.mode == "error":
        emit("error", session_id=start["session_id"], code="FAKE_DECLARED_ERROR")
        return 3
    if args.mode == "cancelable":
        if command().get("command") == "cancel":
            emit("cancelled", session_id=start["session_id"])
            return 0
        emit("error", session_id=start["session_id"], code="PROTOCOL_CANCEL_REQUIRED")
        return 2
    while True:
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
