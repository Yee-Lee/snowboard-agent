"""Deterministic JSON-lines child used only by the M0 readiness packet."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from typing import Any


PROTOCOL = "m0-dummy/1"


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("cooperative", "ignore-term"),
        default="cooperative",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "ignore-term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

    emit({"protocol": PROTOCOL, "state": "READY", "type": "READY"})

    for raw_line in sys.stdin:
        try:
            request = json.loads(raw_line)
        except json.JSONDecodeError:
            emit({"code": "INVALID_JSON", "type": "ERROR"})
            continue

        request_id = request.get("request_id")
        operation = request.get("op")

        if operation == "ping":
            emit(
                {
                    "request_id": request_id,
                    "type": "RESULT",
                    "value": "pong",
                }
            )
        elif operation == "sleep":
            seconds = min(max(float(request.get("seconds", 0.0)), 0.0), 30.0)
            time.sleep(seconds)
            emit(
                {
                    "request_id": request_id,
                    "type": "RESULT",
                    "value": "slept",
                }
            )
        elif operation == "shutdown":
            emit(
                {
                    "request_id": request_id,
                    "type": "RESULT",
                    "value": "shutdown",
                }
            )
            return 0
        else:
            emit(
                {
                    "code": "UNKNOWN_OPERATION",
                    "request_id": request_id,
                    "type": "ERROR",
                }
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
