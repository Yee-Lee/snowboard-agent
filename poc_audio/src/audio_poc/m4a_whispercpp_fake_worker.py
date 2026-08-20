"""Fake native protocol peer for local lifecycle tests; never imports a model."""

from __future__ import annotations

import os
import signal
import sys
import time


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "--model":
        return 2
    if sys.argv[2] == "stubborn.bin":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print(f"READY\t1.9.2\t1000\t{os.getpid()}", flush=True)
    for line in sys.stdin:
        command = line.rstrip("\n")
        if command == "QUIT":
            print("BYE", flush=True)
            return 0
        if not command.startswith("TRANSCRIBE\t"):
            print("ERROR\tINVALID_COMMAND", flush=True)
            continue
        path = command.split("\t", 1)[1]
        if path.endswith("hang.wav"):
            time.sleep(60)
            continue
        transcript = "今天外面的天氣很舒服".encode("utf-8").hex()
        print(f"RESULT\t{transcript}\t1200\t2400\t102400", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
