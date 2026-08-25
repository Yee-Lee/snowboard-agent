from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_failure_runner import M4FailureRunner  # noqa: E402
from audio_poc.m4_packet import FAILURE_ROWS  # noqa: E402


def cleanup() -> dict[str, int]:
    return {
        "child_processes": 0, "threads": 0, "tasks": 0, "iterators": 0,
        "streams": 0, "file_descriptors": 0, "device_owners": 0,
    }


class Adapter:
    async def inject(self, scenario: str, probe: dict[str, object]) -> dict[str, object]:
        return {
            "terminal_status": {"error": "ERROR", "timeout": "TIMEOUT", "cancel": "CANCELLED", "force_abort": "FORCE_ABORTED"}[scenario],
            "injection_source": "CONTROLLED_FORCE_ABORT_DOUBLE" if scenario == "force_abort" else "ACTUAL_FINALIST",
            "injection_observed": True, "force_abort_used": scenario == "force_abort", "cleanup": cleanup(),
        }

    async def recover(self, probe: dict[str, object]) -> dict[str, object]:
        return {"terminal_status": "SUCCESS", "same_finalist": True, "cleanup": cleanup()}


class BrokenAdapter(Adapter):
    async def inject(self, scenario: str, probe: dict[str, object]) -> dict[str, object]:
        value = await super().inject(scenario, probe)
        if scenario == "cancel":
            value["terminal_status"] = "SUCCESS"
        return value


class M4FailureRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_exact_catalog_and_requires_recovery(self) -> None:
        cases = await M4FailureRunner({name: Adapter() for name in ("vad", "asr", "tts")}).run({
            "vad": {"session_id": "v"}, "asr": {"session_id": "a"}, "tts": {"session_id": "t"},
        })
        self.assertEqual([(item["test_id"], item["domain"], item["scenario"]) for item in cases], list(FAILURE_ROWS))
        self.assertEqual(cases[3]["injection_source"], "CONTROLLED_FORCE_ABORT_DOUBLE")

    async def test_wrong_terminal_fails_before_evidence_bundle(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "did not reach CANCELLED"):
            await M4FailureRunner({
                "vad": Adapter(), "asr": BrokenAdapter(), "tts": Adapter(),
            }).run({"vad": {}, "asr": {}, "tts": {}})


if __name__ == "__main__":
    unittest.main()
