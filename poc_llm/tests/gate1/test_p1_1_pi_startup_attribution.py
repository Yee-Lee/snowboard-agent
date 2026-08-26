from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from poc_llm.tools.run_p1_1_pi_startup_attribution import (
    fresh_install_paths,
    observation_viable,
    stage_durations,
)


ROOT = Path(__file__).resolve().parents[3]
PROFILES = ROOT / "poc_llm/fixtures/gate1/p1-1-startup-profiles-v1.json"
PACKET = ROOT / "poc_llm/tests/gate1/P1.1-PI-STARTUP-ATTRIBUTION-PACKET-001.md"
SCHEMA = ROOT / "poc_llm/evidence/gate1/p1-1-pi-startup-attribution-v1.schema.json"
LOCK = ROOT / "poc_llm/harness/p1-1-pi-startup-attribution-lock-v1.json"


class P11PiStartupAttributionTests(unittest.TestCase):
    def test_offline_installer_receives_a_nonexistent_target(self) -> None:
        parent, target = fresh_install_paths()
        try:
            self.assertTrue(parent.is_dir())
            self.assertFalse(target.exists())
            self.assertEqual(target.parent, parent)
        finally:
            parent.rmdir()

    def test_lock_authenticates_every_p1_1_artifact(self) -> None:
        import hashlib

        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "P1.1-PI-STARTUP-ATTRIBUTION-001")
        self.assertEqual(lock["gate_credit"], "FORBIDDEN")
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, item["sha256"], path)

    def test_profiles_are_frozen_and_preserve_the_contract_envelope(self) -> None:
        profiles = json.loads(PROFILES.read_text(encoding="utf-8"))
        self.assertTrue(profiles["diagnostic_only"])
        self.assertEqual(profiles["gate_credit"], "FORBIDDEN")
        self.assertEqual(
            [item["profile_id"] for item in profiles["profiles"]],
            ["baseline"],
        )
        self.assertIsNone(profiles["profiles"][0]["max_num_tokens"])
        self.assertTrue(profiles["profiles"][0]["enable_benchmark"])
        self.assertIn("bounded_context", profiles["deferred_until_after_baseline_analysis"])

    def test_packet_forbids_credit_and_engine_after_ready(self) -> None:
        packet = PACKET.read_text(encoding="utf-8")
        self.assertIn("Gate/P credit**: `FORBIDDEN`", packet)
        self.assertIn("Never move Engine construction after READY", packet)
        self.assertIn("without a removal recommendation", packet)
        self.assertIn("fresh run-scoped receipt", packet)
        self.assertIn("never reused", packet)

    def test_viability_requires_ready_generation_and_cleanup(self) -> None:
        viable = {
            "eventual_ready_ms": 9999.0,
            "ping_pong": True,
            "generation_terminal": "RESULT",
            "shutdown_ack": True,
            "cleanup": {"process_group_absent": True},
        }
        self.assertTrue(observation_viable(viable))
        for key, value in (
            ("eventual_ready_ms", 10000.001),
            ("ping_pong", False),
            ("generation_terminal", "ERROR"),
            ("shutdown_ack", False),
        ):
            changed = dict(viable)
            changed[key] = value
            self.assertFalse(observation_viable(changed))

    def test_stage_parser_uses_monotonic_markers(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            stderr = Path(directory) / "probe.stderr"
            stderr.write_text(
                "P1_1_STAGE adapter_main_start 11000000\n"
                "P1_1_STAGE engine_start 12000000\n"
                "native log\n"
                "P1_1_STAGE engine_end 17000000\n",
                encoding="utf-8",
            )
            stages = stage_durations(stderr, 10_000_000)
        self.assertEqual(stages["spawn_to_adapter_main"], 1.0)
        self.assertEqual(stages["engine"], 5.0)

    def test_schema_rejects_gate_credit(self) -> None:
        validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        self.assertFalse(validator.is_valid({"gate_credit": "P1"}))


if __name__ == "__main__":
    unittest.main()
