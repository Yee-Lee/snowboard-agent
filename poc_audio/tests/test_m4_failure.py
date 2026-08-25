from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_failure import FAILURE_TEST_ID, TERMINALS, validate_failure_bundle  # noqa: E402
from audio_poc.m4_packet import FAILURE_ROWS  # noqa: E402


def zero_cleanup() -> dict[str, int]:
    return {
        "child_processes": 0, "threads": 0, "tasks": 0, "iterators": 0,
        "streams": 0, "file_descriptors": 0, "device_owners": 0,
    }


def bundle() -> dict[str, object]:
    cases = []
    for test_id, domain, scenario in FAILURE_ROWS:
        cases.append({
            "test_id": test_id, "domain": domain, "scenario": scenario,
            "terminal_status": TERMINALS[scenario],
            "injection_source": "CONTROLLED_FORCE_ABORT_DOUBLE" if scenario == "force_abort" else "ACTUAL_FINALIST",
            "injection_observed": True, "duration_ms": 12.5,
            "force_abort_used": scenario == "force_abort", "cleanup": zero_cleanup(),
            "recovery": {
                "attempted": True, "terminal_status": "SUCCESS", "same_finalist": True,
                "cleanup": zero_cleanup(),
            },
        })
    return {
        "schema_version": "1.0", "packet_id": "M4-COMBINED-VALIDATION-TEST-PACKET-001",
        "test_id": FAILURE_TEST_ID, "publication_status": "DRAFT_USER_CONFIRMATION_PENDING",
        "audio_execution_sha": "a" * 40, "core_execution_sha": "6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf",
        "controlled_evidence": {"locator": "controlled://m4/failure", "sha256": "c" * 64},
        "cases": cases, "cleanup": zero_cleanup(), "proposed_disposition": "PASS",
        "decision_boundary": "DRAFT: User confirmation is required before publication.",
    }


class M4FailureBundleTests(unittest.TestCase):
    def test_bundle_locks_all_twelve_cases_and_recovery(self) -> None:
        validate_failure_bundle(bundle())

    def test_nonfinalist_injection_or_residue_fails_closed(self) -> None:
        changed = copy.deepcopy(bundle())
        changed["cases"][0]["injection_source"] = "CONTROLLED_FORCE_ABORT_DOUBLE"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "injection source"):
            validate_failure_bundle(changed)  # type: ignore[arg-type]
        changed = copy.deepcopy(bundle())
        changed["cases"][3]["recovery"]["cleanup"]["device_owners"] = 1  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "cleanup residue"):
            validate_failure_bundle(changed)  # type: ignore[arg-type]

    def test_force_abort_requires_the_controlled_double_and_abort_proof(self) -> None:
        changed = copy.deepcopy(bundle())
        changed["cases"][3]["force_abort_used"] = False  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "force-abort proof"):
            validate_failure_bundle(changed)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
