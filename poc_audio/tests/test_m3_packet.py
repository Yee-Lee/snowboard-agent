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

from audio_poc.m3_packet import load_packet, validate_packet, validate_repo_inputs  # noqa: E402
from audio_poc.m3_authorization import (  # noqa: E402
    validate_m3_result,
    validate_signoff_document,
)
from audio_poc.run_m3_qualification import run_fake_lifecycle  # noqa: E402
from audio_poc.m3_summary import EXPECTED_TEST_IDS, build_summary  # noqa: E402


PACKET_PATH = REPO_ROOT / "poc_audio/manifests/m3_risk_qualification_packet.json"


class M3PacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))

    def test_user_approved_packet_and_repo_inputs_validate(self) -> None:
        packet = load_packet(PACKET_PATH)
        validate_repo_inputs(packet, REPO_ROOT)
        self.assertFalse(packet["authority"]["formal_execution_authorized"])
        self.assertEqual(
            packet["source"]["core_hal_execution_sha"],
            "6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf",
        )
        self.assertEqual(len(packet["fixtures"]["vad"]), 8)
        self.assertEqual(len(packet["fixtures"]["asr"]), 5)
        self.assertEqual(len(packet["fixtures"]["tts"]), 6)

    def test_packet_rejects_automatic_small_q8_fallback(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["candidates"]["asr_fallback"]["automatic_execution"] = True
        with self.assertRaisesRegex(ValueError, "must not execute automatically"):
            validate_packet(changed)

    def test_packet_rejects_missing_vad_category(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["fixtures"]["vad"].pop()
        with self.assertRaisesRegex(ValueError, "eight approved"):
            validate_packet(changed)

    def test_packet_rejects_capture_duration_drift(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["capture_cases"][0]["frames_20ms"] += 1
        with self.assertRaisesRegex(ValueError, "capture catalog"):
            validate_packet(changed)

    def test_packet_rejects_poc_supplied_p9_substitute(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["p9"]["allow_poc_substitute"] = True
        with self.assertRaisesRegex(ValueError, "must not invent"):
            validate_packet(changed)

    def test_packet_rejects_changed_p9_artifact(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["p9"]["sha256"]["runner"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "checksum lock"):
            validate_packet(changed)

    def test_core_signoff_rejects_old_hal_without_output_adaptation(self) -> None:
        signoff = {
            "schema_version": "1.0",
            "status": "CORE_PACKET_SIGNED_OFF",
            "packet_id": "M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001",
            "response_id": "RESP-AUDIO-M3-PACKET-001",
            "poc_execution_sha": "1" * 40,
            "core_execution_sha": "5c9e5aac47e7f4f0dd168d8c75541438ee74f858",
            "core_acceptance_sha": "2" * 40,
            "packet_manifest_sha256": "3" * 64,
        }
        with self.assertRaisesRegex(ValueError, "lacks the required output adaptation"):
            validate_signoff_document(signoff)

    def test_core_signoff_requires_packet_pinned_hal(self) -> None:
        signoff = {
            "schema_version": "1.0",
            "status": "CORE_PACKET_SIGNED_OFF",
            "packet_id": "M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001",
            "response_id": "RESP-AUDIO-M3-PACKET-001",
            "poc_execution_sha": "1" * 40,
            "core_execution_sha": "2" * 40,
            "core_acceptance_sha": "3" * 40,
            "packet_manifest_sha256": "4" * 64,
        }
        with self.assertRaisesRegex(ValueError, "packet-pinned HAL SHA"):
            validate_signoff_document(signoff)

    def test_pass_result_requires_zero_complete_cleanup_proof(self) -> None:
        result = {
            "schema_version": "1.0",
            "packet_id": "M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001",
            "test_id": "M3-LIFE-01",
            "publication_status": "DRAFT_USER_CONFIRMATION_PENDING",
            "result": "PASS",
            "poc_execution_sha": "1" * 40,
            "core_execution_sha": "2" * 40,
            "command": ["runner", "lifecycle"],
            "cleanup": {
                "child_processes": 0,
                "threads": 0,
                "tasks": 0,
                "iterators": 0,
                "streams": 0,
                "file_descriptors": 0,
                "device_owners": 0,
            },
            "controlled_evidence": {"locator": "controlled://m3/run", "sha256": "3" * 64},
        }
        validate_m3_result(result)
        result["cleanup"]["device_owners"] = 1
        with self.assertRaisesRegex(ValueError, "zero cleanup residue"):
            validate_m3_result(result)


class M3FakeLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_dedicated_fake_paths_are_bounded_and_clean(self) -> None:
        results = await run_fake_lifecycle("0" * 40)
        self.assertEqual(len(results), 11)
        self.assertTrue(all(result["cleanup"]["clean"] for result in results))
        self.assertEqual(
            [result["scenario"] for result in results if result["scenario"].startswith("reopen-")],
            [f"reopen-{index}" for index in range(1, 6)],
        )


class M3SummaryTests(unittest.TestCase):
    def test_complete_summary_requires_offline_and_paired_fixture_proof(self) -> None:
        import tempfile

        signoff = {"poc_execution_sha": "1" * 40, "core_execution_sha": "2" * 40}
        phase_by_id = {
            "M3-TTS-SET-01": "tts",
            "M3-ASR-DIRECT-PCM-BASELINE-001": "asr-direct",
            "M3-ASR-HAL-PATH-001": "asr-hal",
            "M3-VAD-SET-01": "vad-hal",
            "M3-LIFE-05": "candidate-lifecycle",
            "M3-LIFE-06": "candidate-lifecycle",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, test_id in enumerate(sorted(EXPECTED_TEST_IDS)):
                phase = phase_by_id.get(test_id, "capture")
                details = {}
                if phase in {"tts", "asr-direct", "asr-hal", "vad-hal", "candidate-lifecycle"}:
                    details["network"] = {"network_disabled": True}
                if test_id in {
                    "M3-ASR-DIRECT-PCM-BASELINE-001", "M3-ASR-HAL-PATH-001",
                }:
                    details["fixture_lock_sha256"] = "4" * 64
                document = {
                    "schema_version": "1.0",
                    "packet_id": "M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001",
                    "test_id": test_id,
                    "publication_status": "DRAFT_USER_CONFIRMATION_PENDING",
                    "result": "PASS",
                    "poc_execution_sha": "1" * 40,
                    "core_execution_sha": "2" * 40,
                    "command": ["runner", test_id],
                    "phase": phase,
                    "cleanup": {
                        "child_processes": 0, "threads": 0, "tasks": 0,
                        "iterators": 0, "streams": 0, "file_descriptors": 0,
                        "device_owners": 0,
                    },
                    "controlled_evidence": {
                        "locator": f"controlled://m3/{test_id}", "sha256": "3" * 64,
                    },
                    "details": details,
                }
                (root / f"{index:02d}.json").write_text(json.dumps(document), encoding="utf-8")
            summary = build_summary(root, signoff)
        self.assertEqual(summary["result_count"], len(EXPECTED_TEST_IDS))
        self.assertEqual(summary["proposed_disposition"], "PASS")
        self.assertEqual(summary["publication_status"], "DRAFT_USER_CONFIRMATION_PENDING")


if __name__ == "__main__":
    unittest.main()
