from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_packet import (  # noqa: E402
    FAILURE_ROWS,
    SESSION_ROWS,
    load_packet,
    validate_fake_result,
    validate_packet,
    validate_repo_inputs,
)
from audio_poc.run_m4_combined import build_fake_result  # noqa: E402


PACKET_PATH = REPO_ROOT / "poc_audio/manifests/m4_combined_packet.json"


class M4PacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))

    def test_user_approved_packet_and_repo_inputs_validate(self) -> None:
        packet = load_packet(PACKET_PATH)
        validate_repo_inputs(packet, REPO_ROOT)
        self.assertFalse(packet["authority"]["formal_execution_authorized"])
        self.assertEqual(len(packet["fixtures"]["sessions"]), 20)
        self.assertEqual(len(packet["failure_injections"]), 12)
        self.assertEqual(packet["p9"]["catalog"], [row[0] for row in SESSION_ROWS])
        self.assertEqual(packet["fixtures"]["sessions"][7][2], "asr-pause-038")
        self.assertEqual(
            packet["p9"]["orchestration_policy"],
            "VAD_ASR_THEN_P9_INFER_THEN_REASONER_TTS",
        )

    def test_packet_rejects_formal_execution_claim(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["authority"]["formal_execution_authorized"] = True
        with self.assertRaisesRegex(ValueError, "fail closed for formal execution"):
            validate_packet(changed)

    def test_packet_rejects_session_reordering(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["fixtures"]["sessions"][0], changed["fixtures"]["sessions"][1] = (
            changed["fixtures"]["sessions"][1], changed["fixtures"]["sessions"][0],
        )
        with self.assertRaisesRegex(ValueError, "20-session catalog mismatch"):
            validate_packet(changed)

    def test_packet_rejects_p9_profile_tuning(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["p9"]["profile"]["reserve_mib"] = 2048
        with self.assertRaisesRegex(ValueError, "artifact/profile lock mismatch"):
            validate_packet(changed)

    def test_packet_rejects_original_p9_overlap_policy(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["p9"]["orchestration_policy"] = "FULL_SESSION_OVERLAP"
        with self.assertRaisesRegex(ValueError, "P9.1 orchestration policy mismatch"):
            validate_packet(changed)

    def test_packet_rejects_superseded_hard_failure_fixture(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["fixtures"]["sessions"][7][2] = "asr-pause-037"
        with self.assertRaisesRegex(ValueError, "20-session catalog mismatch"):
            validate_packet(changed)

    def test_packet_rejects_missing_failure_case(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["failure_injections"].pop()
        with self.assertRaisesRegex(ValueError, "failure-injection catalog mismatch"):
            validate_packet(changed)

    def test_schemas_are_valid_json_and_lock_packet_result_identity(self) -> None:
        for name in ("m4_combined_packet.schema.json", "m4_combined_result.schema.json"):
            schema = json.loads((REPO_ROOT / "poc_audio/schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        result_schema = json.loads(
            (REPO_ROOT / "poc_audio/schemas/m4_combined_result.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            result_schema["properties"]["packet_id"]["const"],
            "M4-COMBINED-VALIDATION-TEST-PACKET-001",
        )


class M4FakeCombinedTests(unittest.IsolatedAsyncioTestCase):
    async def test_twenty_persistent_sessions_and_all_failure_recoveries_are_clean(self) -> None:
        packet = load_packet(PACKET_PATH)
        result = await build_fake_result("0" * 40)
        validate_fake_result(result, packet)
        self.assertEqual(result["model_load_counts"], {"vad": 1, "asr": 1, "tts": 1})
        self.assertEqual(len(result["sessions"]), 20)
        self.assertEqual(len(result["failure_injections"]), len(FAILURE_ROWS))
        self.assertTrue(all(item["case_pass"] for item in result["failure_injections"]))
        self.assertTrue(all(item["recovery_pass"] for item in result["failure_injections"]))
        self.assertEqual(
            [item["terminal_status"] for item in result["failure_injections"]],
            [
                "error", "timeout", "cancelled", "force_aborted",
                "error", "timeout", "cancelled", "force_aborted",
                "error", "timeout", "cancelled", "force_aborted",
            ],
        )

    async def test_fake_result_cannot_claim_hardware_evidence(self) -> None:
        packet = load_packet(PACKET_PATH)
        result = await build_fake_result("1" * 40)
        changed = copy.deepcopy(result)
        changed["evidence_eligible"] = True
        with self.assertRaisesRegex(ValueError, "hardware-ineligible"):
            validate_fake_result(changed, packet)

    async def test_fake_result_rejects_cleanup_residue(self) -> None:
        packet = load_packet(PACKET_PATH)
        result = await build_fake_result("2" * 40)
        result["failure_injections"][0]["cleanup"]["child_processes"] = 1
        result["failure_injections"][0]["cleanup"]["clean"] = False
        with self.assertRaisesRegex(ValueError, "failure cleanup residue"):
            validate_fake_result(result, packet)


if __name__ == "__main__":
    unittest.main()
