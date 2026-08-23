#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from poc_llm.tools.run_gate1_arm64_smoke import (
    SmokeFailure,
    network_isolated,
    read_frame,
    stop,
)


class Arm64SmokeRunnerTest(unittest.TestCase):
    def test_network_isolation_accepts_no_v4_and_loopback_only_v6(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            route4 = root / "route"
            route6 = root / "ipv6_route"
            route4.write_text("Iface Destination Gateway\n", encoding="ascii")
            route6.write_text("0 0 0 0 0 0 0 0 0 lo\n", encoding="ascii")
            self.assertTrue(network_isolated(route4, route6))

    def test_network_isolation_rejects_an_ipv4_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            route4 = root / "route"
            route6 = root / "ipv6_route"
            route4.write_text("Iface Destination Gateway\nenp0s1 00000000 00000000\n", encoding="ascii")
            route6.write_text("", encoding="ascii")
            self.assertFalse(network_isolated(route4, route6))

    def test_read_frame_rejects_protocol_invalid_json(self) -> None:
        validator = Draft202012Validator({
            "type": "object",
            "additionalProperties": False,
            "required": ["type"],
            "properties": {"type": {"const": "READY"}},
        })
        read_fd, write_fd = os.pipe()
        with os.fdopen(write_fd, "w", encoding="utf-8") as writer:
            writer.write('{"type":"RESULT"}\n')
        with os.fdopen(read_fd, "r", encoding="utf-8") as reader:
            with self.assertRaises(SmokeFailure):
                read_frame(reader, 0.1, validator)

    def test_stop_reaps_process_group(self) -> None:
        process = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(30)"],
            start_new_session=True,
            text=True,
        )
        result = stop(process, 0.2, 0.2)
        self.assertTrue(result["waited"])
        self.assertTrue(result["term_sent"])
        self.assertTrue(result["process_group_absent"])

    def test_report_never_requires_model_text(self) -> None:
        source = Path("poc_llm/tools/run_gate1_arm64_smoke.py").read_text(encoding="utf-8")
        self.assertNotIn('"response": terminal', source)
        self.assertNotIn('"prompt":', source)


if __name__ == "__main__":
    unittest.main()
