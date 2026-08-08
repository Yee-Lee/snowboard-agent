"""Deterministic child process used to prove harness lifecycle behaviour."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time


def emit(message: dict[str, object]) -> None:
    print(json.dumps(message, sort_keys=True), flush=True)


def exit_on_term(_signum: int, _frame: object) -> None:
    raise SystemExit(0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        required=True,
        choices=("success", "error", "hang", "stubborn"),
    )
    args = parser.parse_args()

    if args.mode == "stubborn":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    else:
        signal.signal(signal.SIGTERM, exit_on_term)

    emit({"event": "ready", "protocol": 1})
    if args.mode == "success":
        emit({"event": "result", "value": "deterministic"})
        return 0
    if args.mode == "error":
        emit({"event": "error", "code": "FAKE_DECLARED_ERROR"})
        return 3

    while True:
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
