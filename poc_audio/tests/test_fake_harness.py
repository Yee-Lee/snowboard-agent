from __future__ import annotations

import json
import sys
import unittest
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.harness import FakeProcessHarness, Scenario  # noqa: E402
from audio_poc.fixture_recorder import (  # noqa: E402
    build_capture_items,
    load_plan,
    select_stage_items,
    sha256_file,
    validate_wav,
    verify_records,
)
from audio_poc.fixture_monitor import duplicate_channel_to_stereo  # noqa: E402
from audio_poc.models import TerminalStatus  # noqa: E402
from audio_poc.validation import (  # noqa: E402
    validate_candidate_manifest,
    validate_fixture_catalog,
    validate_run_result,
)


class FakeHarnessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.harness = FakeProcessHarness("0" * 40)

    async def assert_scenario(
        self,
        scenario: Scenario,
        expected: TerminalStatus,
    ) -> None:
        result = await self.harness.run(scenario)
        self.assertEqual(result.terminal_status, expected)
        self.assertTrue(result.cleanup.clean)
        self.assertEqual(result.cleanup.child_processes, 0)
        validate_run_result(result.to_dict())

    async def test_success(self) -> None:
        await self.assert_scenario(
            Scenario("success", "success", timeout_seconds=0.5),
            TerminalStatus.SUCCESS,
        )

    async def test_declared_error(self) -> None:
        await self.assert_scenario(
            Scenario("error", "error", timeout_seconds=0.5),
            TerminalStatus.ERROR,
        )

    async def test_timeout(self) -> None:
        await self.assert_scenario(
            Scenario("timeout", "hang", timeout_seconds=0.08),
            TerminalStatus.TIMEOUT,
        )

    async def test_cancel(self) -> None:
        await self.assert_scenario(
            Scenario(
                "cancel",
                "hang",
                timeout_seconds=1.0,
                cancel_after_seconds=0.05,
            ),
            TerminalStatus.CANCELLED,
        )

    async def test_force_abort(self) -> None:
        result = await self.harness.run(
            Scenario("force_abort", "stubborn", timeout_seconds=0.08)
        )
        self.assertEqual(result.terminal_status, TerminalStatus.FORCE_ABORTED)
        self.assertTrue(result.force_abort_used)
        self.assertTrue(result.cleanup.clean)
        self.assertEqual(result.cleanup.child_processes, 0)
        validate_run_result(result.to_dict())


class TrackedDocumentTests(unittest.TestCase):
    def test_candidate_manifest_and_fixture_catalog(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "poc_audio/manifests/deterministic_fake.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (REPO_ROOT / "poc_audio/fixtures/catalog.json").read_text(
                encoding="utf-8"
            )
        )
        validate_candidate_manifest(manifest, REPO_ROOT)
        validate_fixture_catalog(catalog, REPO_ROOT)

    def test_schema_documents_are_valid_json(self) -> None:
        for path in sorted((REPO_ROOT / "poc_audio/schemas").glob("*.json")):
            with self.subTest(path=path.name):
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_authorized_recording_plan_is_complete_but_not_candidate_ready(self) -> None:
        plan = json.loads(
            (
                REPO_ROOT
                / "poc_audio/fixtures/authorized/recording_plan_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(plan["authorization_status"], "authorized_by_user_designer")
        self.assertFalse(plan["audio_git_tracked"])
        self.assertFalse(plan["candidate_ready"])

        set_counts = {item["class"]: item["count"] for item in plan["sets"]}
        self.assertEqual(
            set_counts,
            {"clear_speech": 25, "pause": 25, "silence": 25, "noise": 25},
        )
        non_speech_seconds = sum(
            item["count"] * item["duration_seconds_each"]
            for item in plan["sets"]
            if item["class"] in {"silence", "noise"}
        )
        self.assertGreaterEqual(non_speech_seconds, 600)

        utterances = plan["utterances"]
        self.assertEqual(len(utterances), 50)
        self.assertEqual(len({item["fixture_id"] for item in utterances}), 50)
        self.assertEqual(
            sum(item["vad_class"] == "clear_speech" for item in utterances), 25
        )
        self.assertEqual(sum(item["vad_class"] == "pause" for item in utterances), 25)
        self.assertTrue(all(item["reference_text"] for item in utterances))

        pilot, formal = plan["collection_stages"]
        self.assertEqual(pilot["stage_id"], "pilot")
        self.assertEqual(pilot["expected_count"], 40)
        self.assertEqual(len(pilot["speech_fixture_ids"]), 20)
        self.assertEqual(len(set(pilot["speech_fixture_ids"])), 20)
        self.assertEqual(formal["stage_id"], "formal")
        self.assertEqual(formal["expected_count"], 100)
        self.assertEqual(formal["remaining_after_pilot"], 60)
        items = build_capture_items(plan)
        self.assertEqual(len(select_stage_items(plan, items, "pilot")), 40)
        self.assertEqual(len(select_stage_items(plan, items, "formal")), 60)

    def test_fixture_recorder_validates_a_complete_local_manifest(self) -> None:
        plan_path = REPO_ROOT / "poc_audio/fixtures/authorized/recording_plan_v1.json"
        plan = load_plan(plan_path)
        for capture_set in plan["sets"]:
            capture_set["duration_seconds_each"] = 1
        plan["_path"] = str(plan_path)
        items = build_capture_items(plan)
        self.assertEqual(len(items), 100)

        with self.subTest("native wav metadata"):
            import tempfile

            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                records = {}
                for item in items:
                    wav_path = root / f"{item.fixture_id}.wav"
                    with wave.open(str(wav_path), "wb") as generated:
                        generated.setnchannels(2)
                        generated.setsampwidth(4)
                        generated.setframerate(48000)
                        generated.writeframes(b"\x00" * (48000 * 2 * 4))
                    metadata = validate_wav(wav_path, plan["native_capture"])
                    records[item.fixture_id] = {
                        "fixture_id": item.fixture_id,
                        "vad_class": item.vad_class,
                        "category": item.category,
                        "file": wav_path.name,
                        "sha256": sha256_file(wav_path),
                        "metadata": metadata,
                    }
                (root / "fixture_manifest.json").write_text(
                    json.dumps(
                        {
                            "schema_version": "1.0",
                            "plan_id": plan["plan_id"],
                            "plan_sha256": sha256_file(plan_path),
                            "authorization_confirmed": True,
                            "native_capture": plan["native_capture"],
                            "records": records,
                        }
                    ),
                    encoding="utf-8",
                )
                outcome = verify_records(plan, root)
                self.assertEqual(outcome["summary"]["result"], "PASS")
                self.assertEqual(outcome["summary"]["valid_files"], 100)
                self.assertEqual(outcome["summary"]["non_speech_seconds"], 50)

    def test_monitor_duplicates_the_requested_channel_without_gain(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.wav"
            destination = root / "monitor.wav"
            with wave.open(str(source), "wb") as generated:
                generated.setnchannels(2)
                generated.setsampwidth(4)
                generated.setframerate(48000)
                generated.writeframes((123456).to_bytes(4, "little", signed=True))
                generated.writeframes((-654321).to_bytes(4, "little", signed=True))
            duplicate_channel_to_stereo(source, destination, 0)
            with wave.open(str(destination), "rb") as monitored:
                payload = monitored.readframes(1)
            left = int.from_bytes(payload[:4], "little", signed=True)
            right = int.from_bytes(payload[4:], "little", signed=True)
            self.assertEqual((left, right), (123456, 123456))


if __name__ == "__main__":
    unittest.main()
