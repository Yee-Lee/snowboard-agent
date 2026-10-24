#!/usr/bin/env python3
"""Run the installed M5.tool app with controlled mock Tool and Vision outcomes.

Audio, ASR, TTS, GPIO, Display and Gemma use the ordinary product composition.
Press the physical button and speak to exercise a scenario; Ctrl+C stops it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sbd.action.tool.mock_send import MockSend
from sbd.adaptor.errors import AdapterError
from sbd.core import m2_composition
from sbd.core.config.loader import load_config
from sbd.main import bootstrap_logging, run_app
from sbd.perception.look.vision import MockVisionAdapter, VisionResult


_OBSERVATIONS = {
    "book": VisionResult("偵測到一本書。"),
    "cup": VisionResult("偵測到一個馬克杯。"),
    "empty": VisionResult("本次沒有辨識到支援的物件"),
}


class _TimeoutVision(MockVisionAdapter):
    async def describe(self, image: bytes) -> VisionResult:
        self.entered.set()
        await asyncio.Future()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--vision", choices=(*_OBSERVATIONS, "error", "timeout"),
                        default="book")
    parser.add_argument("--send", choices=("ok", "error"), default="ok")
    args = parser.parse_args()
    config = load_config(local_path=args.config)
    if config.cognition.llm.profile_id != "core-m5-tool-001":
        parser.error("M5.tool product config required")

    sends: list[MockSend] = []

    def vision_fixture() -> MockVisionAdapter:
        if args.vision == "timeout":
            return _TimeoutVision()
        outcome = (AdapterError("VISION_FIXTURE_ERROR") if args.vision == "error"
                   else _OBSERVATIONS[args.vision])
        return MockVisionAdapter(outcomes=(outcome,) * 8)

    def send_fixture() -> MockSend:
        handler = MockSend(outcome=args.send)
        sends.append(handler)
        return handler

    m2_composition.MockVisionAdapter = vision_fixture
    m2_composition.MockSend = send_fixture
    bootstrap_logging()
    status = asyncio.run(run_app(str(args.config)))
    print(json.dumps({"vision_fixture": args.vision, "send_mode": args.send,
                      "dispatch_count": sum(len(handler.calls) for handler in sends),
                      "exit_code": status}, separators=(",", ":")))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
