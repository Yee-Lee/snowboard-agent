"""Controlled, non-candidate process used only for M4 force-abort proof."""

from __future__ import annotations

import argparse
import signal
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=("vad", "asr", "tts"), required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print(f"READY\tCONTROLLED_FORCE_ABORT_DOUBLE\t{args.domain}", flush=True)
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
