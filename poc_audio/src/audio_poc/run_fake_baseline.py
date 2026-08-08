"""Run the M1 deterministic fake baseline and write ignored raw JSON evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .harness import FakeProcessHarness, Scenario
from .models import TerminalStatus
from .validation import (
    validate_candidate_manifest,
    validate_fixture_catalog,
    validate_run_result,
)


EXPECTED = {
    "success": TerminalStatus.SUCCESS,
    "error": TerminalStatus.ERROR,
    "timeout": TerminalStatus.TIMEOUT,
    "cancel": TerminalStatus.CANCELLED,
    "force_abort": TerminalStatus.FORCE_ABORTED,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ("git", "-C", str(root), *args),
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


async def run(args: argparse.Namespace) -> int:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required")

    root = repo_root()
    dirty = git_output(root, "status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise RuntimeError("Git worktree must be clean for a formal fake baseline")
    source_sha = git_output(root, "rev-parse", "HEAD")

    manifest_path = root / "poc_audio/manifests/deterministic_fake.json"
    catalog_path = root / "poc_audio/fixtures/catalog.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    validate_candidate_manifest(manifest, root)
    validate_fixture_catalog(catalog, root)

    evidence_dir = args.evidence_dir or (
        root
        / "poc_audio/evidence/m1"
        / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-fake"
    )
    evidence_dir.mkdir(parents=True, exist_ok=False)

    scenarios = (
        Scenario("success", "success", timeout_seconds=0.5),
        Scenario("error", "error", timeout_seconds=0.5),
        Scenario("timeout", "hang", timeout_seconds=0.08),
        Scenario(
            "cancel",
            "hang",
            timeout_seconds=1.0,
            cancel_after_seconds=0.05,
        ),
        Scenario("force_abort", "stubborn", timeout_seconds=0.08),
    )
    harness = FakeProcessHarness(source_sha)
    results = []
    for scenario in scenarios:
        result = await harness.run(scenario)
        document = result.to_dict()
        validate_run_result(document)
        (evidence_dir / f"{scenario.name}.json").write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        results.append(document)

    failures = [
        document["scenario"]
        for document in results
        if document["terminal_status"] != EXPECTED[document["scenario"]].value
        or not document["cleanup"]["clean"]
    ]
    summary = {
        "test_id": "M1-FAKE-001",
        "source_sha": source_sha,
        "result": "PASS" if not failures else "FAIL",
        "scenario_count": len(results),
        "failures": failures,
        "terminal_statuses": {
            document["scenario"]: document["terminal_status"] for document in results
        },
        "cleanup_all_zero": all(document["cleanup"]["clean"] for document in results),
    }
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"M1 fake baseline: {summary['result']}; evidence: {evidence_dir}")
    return 0 if not failures else 1


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    sys.exit(main())
