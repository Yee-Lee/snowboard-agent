import json
import re
import unittest
from pathlib import Path

from asr_r1.protocol import ErrorCode, EventKind, LifecycleOperation


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent


def load(relative: str) -> dict:
    with (PACKAGE_ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


class SchemaAndManifestTest(unittest.TestCase):
    def test_json_files_parse(self) -> None:
        for path in sorted((PACKAGE_ROOT / "manifests").glob("*.json")) + sorted(
            (PACKAGE_ROOT / "schemas").glob("*.json")
        ):
            with self.subTest(path=path.name):
                with path.open(encoding="utf-8") as handle:
                    self.assertIsInstance(json.load(handle), dict)

    def test_governed_artifact_paths_are_repo_relative_and_resolve(self) -> None:
        expected = [
            "asr_r1/manifests/candidate_tracker.json",
            "asr_r1/manifests/control_provenance.json",
            "asr_r1/manifests/fixture_reuse_audit_plan.json",
            "asr_r1/manifests/m1_baseline_method.json",
            "asr_r1/manifests/m1_identity_screening.json",
            "asr_r1/manifests/m1_smoke_fixture.json",
            "asr_r1/schemas/lifecycle_command.schema.json",
            "asr_r1/schemas/pcm_chunk.schema.json",
            "asr_r1/schemas/streaming_event.schema.json",
            "asr_r1/protocol.py",
            "asr_r1/fake_runtime.py",
        ]
        for relative in expected:
            with self.subTest(path=relative):
                path = Path(relative)
                self.assertFalse(path.is_absolute())
                self.assertTrue((REPO_ROOT / path).is_file())

    def test_python_sources_do_not_hardcode_host_paths(self) -> None:
        host_path = re.compile(
            r"(?:['\"]/(?:home|Users|workspace)/|['\"][A-Za-z]:[\\/])"
        )
        for path in sorted(PACKAGE_ROOT.rglob("*.py")):
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                source = path.read_text(encoding="utf-8")
                self.assertIsNone(host_path.search(source))

    def test_schema_enums_match_python_protocol(self) -> None:
        event = load("schemas/streaming_event.schema.json")
        lifecycle = load("schemas/lifecycle_command.schema.json")
        self.assertEqual(
            {item.value for item in EventKind},
            set(event["properties"]["kind"]["enum"]),
        )
        self.assertEqual(
            {item.value for item in ErrorCode},
            set(event["properties"]["error"]["properties"]["code"]["enum"]),
        )
        self.assertEqual(
            {item.value for item in LifecycleOperation},
            set(lifecycle["properties"]["operation"]["enum"]),
        )

    def test_candidate_tracker_records_metadata_dispositions(self) -> None:
        tracker = load("manifests/candidate_tracker.json")
        self.assertEqual(5, len(tracker["candidates"]))
        self.assertEqual(
            [
                "asr-sherpa-streaming-zipformer-zh-xlarge-int8-2025-06-30",
                "asr-sherpa-wenet-wenetspeech-streaming-ctc-int8",
                "asr-nvidia-nemotron-3-5-streaming-0-6b-q8-0",
                "asr-sherpa-streaming-zipformer-zh-large-int8-2025-06-30",
                "asr-sherpa-wenet-aishell-streaming-ctc-int8",
            ],
            [item["candidate_id"] for item in tracker["candidates"]],
        )
        self.assertEqual(
            [1, 2, 3, 4, 5],
            [item["development_order"] for item in tracker["candidates"]],
        )
        self.assertEqual(
            {
                "LOCKABLE_METADATA_ONLY",
                "LOCKABLE_MEMORY_CAPPED_PROBE_ONLY",
            },
            {item["identity_status"] for item in tracker["candidates"]},
        )
        self.assertEqual(
            "STOP_USER_ELIMINATED_MEMORY_BUDGET",
            tracker["eliminated_candidates"][0]["identity_status"],
        )
        self.assertIn("REAL_EXECUTION_REQUIRES_FROZEN_PACKET", tracker["status"])

    def test_m1_screen_is_non_formal_and_cost_gated(self) -> None:
        screening = load("manifests/m1_identity_screening.json")
        self.assertFalse(screening["formal_result"])
        self.assertIn("NO_EXECUTION_AUTHORIZATION", screening["status"])
        self.assertEqual(
            ["LOCKABLE"] * 5,
            [row["disposition"] for row in screening["rows"]],
        )
        xlarge = screening["rows"][0]
        self.assertGreater(xlarge["checkpoint"]["artifact_size_bytes"], 500_000_000)
        nemotron = screening["rows"][2]
        self.assertEqual(741_548_352, nemotron["checkpoint"]["size_bytes"])
        self.assertEqual("zh-CN", nemotron["checkpoint"]["language_scope"].split()[1])
        self.assertEqual("STOP", screening["stopped_rows"][0]["disposition"])

    def test_m1_baseline_is_non_formal_memory_capped_and_ordered(self) -> None:
        method = load("manifests/m1_baseline_method.json")
        self.assertFalse(method["formal_result"])
        self.assertEqual(1_000_000_000, method["memory_budget_bytes"])
        self.assertIn("BLOCKED_ON_CONTROLLED_FIXTURE", method["status"])
        self.assertEqual(
            [1, 2, 3, 4, 5],
            [row["development_order"] for row in method["candidate_commands"]],
        )
        self.assertIn("not a formal score", method["interpretation_limit"])

    def test_m1_smoke_fixture_is_regression_only(self) -> None:
        fixture = load("manifests/m1_smoke_fixture.json")
        self.assertEqual("regression_smoke_only", fixture["role"])
        self.assertFalse(fixture["holdout_eligible"])
        self.assertEqual(16_000, fixture["pcm"]["sample_rate_hz"])
        self.assertAlmostEqual(2.66, fixture["pcm"]["duration_seconds"])
        self.assertEqual("NOT_FOUND", fixture["controlled_locator"]["local_availability_at_freeze"])

    def test_control_provenance_is_bound_to_audio_m4(self) -> None:
        provenance = load("manifests/control_provenance.json")
        self.assertEqual(
            "5694ead4ba6be928fdb4dbdf6da7155b214d72bd",
            provenance["historical_control"]["commit"],
        )
        self.assertEqual(
            "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9",
            provenance["whisper_control"]["model"]["sha256"],
        )
        self.assertEqual(
            "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3",
            provenance["silero_control"]["model"]["sha256"],
        )

    def test_fixture_plan_has_no_role_assignment(self) -> None:
        fixtures = load("manifests/fixture_reuse_audit_plan.json")
        self.assertIn("NO_HOLDOUT_ASSIGNED", fixtures["status"])
        self.assertTrue(
            all(item["assigned_role"] is None for item in fixtures["sources_to_audit"])
        )
        self.assertEqual(
            "holdout_eligible_only_after_user_review",
            fixtures["policy"]["role_rules"]["untouched"],
        )
        gates = fixtures["policy"]["milestone_gates"]
        self.assertEqual(
            [
                "AR1M0",
                "AR1M1_ENTRY_BEFORE_REAL_SMOKE",
                "AR1M1_EXIT_AR1M2_ENTRY",
                "BEFORE_AR1M2A_FORMAL",
                "AR1M3_ENTRY_AFTER_PIPELINE_FREEZE",
            ],
            [gate["milestone"] for gate in gates],
        )
        self.assertEqual("PROHIBITED", gates[0]["collection"])
        self.assertIn("QUALIFICATION_ONLY", gates[-1]["collection"])


if __name__ == "__main__":
    unittest.main()
