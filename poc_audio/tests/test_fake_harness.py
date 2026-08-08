from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.harness import FakeProcessHarness, Scenario  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
