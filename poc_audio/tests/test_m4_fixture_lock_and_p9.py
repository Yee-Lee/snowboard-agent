from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_fixture_lock import (  # noqa: E402
    build_fixture_lock,
    load_fixture_lock,
    validate_fixture_lock,
    verify_fixture_files,
)
from audio_poc.m4_p9 import P9Client, locked_p9_paths  # noqa: E402
from audio_poc.m4_packet import SESSION_ROWS  # noqa: E402
from audio_poc.m4_authorization import validate_authorization_document, validate_formal_result  # noqa: E402
from audio_poc.m4_formal import _p9_summary  # noqa: E402


class M4FixtureLockTests(unittest.TestCase):
    @staticmethod
    def _make_fixture(directory: Path, fixture_id: str) -> None:
        with wave.open(str(directory / f"{fixture_id}.wav"), "wb") as destination:
            destination.setnchannels(1)
            destination.setsampwidth(2)
            destination.setframerate(16_000)
            destination.writeframes(b"\x00\x00" * 160)

    def test_lock_binds_all_twenty_wavs_to_the_audio_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_dir = root / "fixtures"
            fixture_dir.mkdir()
            for _session, _category, fixture_id, _tts in SESSION_ROWS:
                self._make_fixture(fixture_dir, fixture_id)
            lock_path = root / "fixture-lock.json"
            lock = build_fixture_lock(REPO_ROOT, fixture_dir, lock_path, "a" * 40)
            self.assertEqual(lock["fixture_count"], 20)
            self.assertEqual(lock["records"][0]["fixture_id"], "asr-clear-002")
            loaded = load_fixture_lock(lock_path, "a" * 40)
            verify_fixture_files(loaded, fixture_dir)

    def test_lock_rejects_sha_and_catalog_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_dir = root / "fixtures"
            fixture_dir.mkdir()
            for _session, _category, fixture_id, _tts in SESSION_ROWS:
                self._make_fixture(fixture_dir, fixture_id)
            lock = build_fixture_lock(REPO_ROOT, fixture_dir, root / "fixture-lock.json", "b" * 40)
            changed = copy.deepcopy(lock)
            changed["records"][0]["fixture_id"] = "asr-clear-999"
            with self.assertRaisesRegex(ValueError, "catalog/order mismatch"):
                validate_fixture_lock(changed)
            with self.assertRaisesRegex(ValueError, "formal Audio SHA"):
                load_fixture_lock(root / "fixture-lock.json", "c" * 40)
            (fixture_dir / "asr-clear-002.wav").write_bytes(b"drift")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_fixture_files(lock, fixture_dir)


class M4P9ClientTests(unittest.TestCase):
    def test_locked_self_test_protocol_exercises_overlap_and_cleanup(self) -> None:
        paths = locked_p9_paths(REPO_ROOT)
        client = P9Client(paths["runner"], paths["schema"], paths["lock"], self_test=True)
        ready = client.start(3.0)
        self.assertFalse(ready["evidence_eligible"])
        result = client.infer_with_workload("m4-test-001", lambda: {"audio": "started"}, 3.0)
        self.assertEqual(result["request_id"], "m4-test-001")
        self.assertEqual(len(result["worker_pids"]), 2)
        shutdown = client.shutdown(3.0)
        self.assertEqual(shutdown["residual_workers"], 0)

    def test_p9_rejects_checksum_mismatch_before_launch(self) -> None:
        paths = locked_p9_paths(REPO_ROOT)
        client = P9Client(paths["runner"].with_name("missing.py"), paths["schema"], paths["lock"])
        with self.assertRaisesRegex(ValueError, "runner checksum mismatch"):
            client.start(1.0)

    def test_p9_begin_and_complete_are_available_to_the_async_coordinator(self) -> None:
        paths = locked_p9_paths(REPO_ROOT)
        client = P9Client(paths["runner"], paths["schema"], paths["lock"], self_test=True)
        client.start(3.0)
        token = client.begin_infer("m4-test-split-001", 3.0)
        self.assertEqual(token["request_id"], "m4-test-split-001")
        complete = client.complete_infer("m4-test-split-001", token["worker_pids"], 3.0)
        self.assertEqual(complete["event"], "INFERENCE_COMPLETE")
        client.shutdown(3.0)

    def test_p9_summary_fails_closed_for_capacity_or_throttle(self) -> None:
        sample = {
            "used_mib": 3500.0, "swap_total_kib": 0, "throttled": "throttled=0x0",
        }
        self.assertTrue(_p9_summary([sample])["all_samples_within_capacity_gate"])
        with self.assertRaisesRegex(RuntimeError, "capacity gate"):
            _p9_summary([{**sample, "used_mib": 3585.0}])
        with self.assertRaisesRegex(RuntimeError, "throttling proof"):
            _p9_summary([{**sample, "throttled": "throttled=0x50000"}])


class M4AuthorizationTests(unittest.TestCase):
    def _authorization(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "status": "M4_FORMAL_EXECUTION_AUTHORIZED",
            "packet_id": "M4-COMBINED-VALIDATION-TEST-PACKET-001",
            "audio_execution_sha": "a" * 40,
            "core_execution_sha": "6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf",
            "packet_manifest_sha256": "b" * 64,
            "user_authorization_id": "USER-M4-PI-001",
            "p9_execution_authorized": True,
        }

    def test_authorization_rejects_unapproved_p9(self) -> None:
        document = self._authorization()
        validate_authorization_document(document)
        document["p9_execution_authorized"] = False
        with self.assertRaisesRegex(ValueError, "explicitly authorize P9"):
            validate_authorization_document(document)

    def test_pass_result_requires_cleanup_and_controlled_evidence(self) -> None:
        result = {
            "schema_version": "1.0",
            "packet_id": "M4-COMBINED-VALIDATION-TEST-PACKET-001",
            "test_id": "M4-P9-001",
            "publication_status": "DRAFT_USER_CONFIRMATION_PENDING",
            "result": "PASS",
            "audio_execution_sha": "a" * 40,
            "core_execution_sha": "6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf",
            "command": ["run-m4"],
            "cleanup": {
                "child_processes": 0, "threads": 0, "tasks": 0, "iterators": 0,
                "streams": 0, "file_descriptors": 0, "device_owners": 0,
            },
            "controlled_evidence": {"locator": "controlled://m4/p9", "sha256": "c" * 64},
            "details": {},
        }
        validate_formal_result(result)
        result["cleanup"]["device_owners"] = 1
        with self.assertRaisesRegex(ValueError, "zero cleanup residue"):
            validate_formal_result(result)


if __name__ == "__main__":
    unittest.main()
