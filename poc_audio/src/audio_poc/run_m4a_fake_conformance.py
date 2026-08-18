"""Run the artifact-independent WP2 M4a protocol conformance kit."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .m4a_conformance import ConformanceScenario, M4aFakeConformanceHarness
from .validation import GIT_SHA_RE, validate_m4a_conformance_result


SCENARIOS = (
    ConformanceScenario("success", "asr", "success", 0.3),
    ConformanceScenario("error", "asr", "error", 0.3),
    ConformanceScenario("timeout", "tts", "hang", 0.05),
    ConformanceScenario("cancel", "tts", "cancelable", 0.3, 0.02),
    ConformanceScenario("force-abort", "asr", "stubborn", 0.05),
    ConformanceScenario("reopen", "tts", "success", 0.3),
)


async def run(source_sha: str) -> list[dict[str, object]]:
    harness = M4aFakeConformanceHarness(source_sha)
    results = []
    for scenario in SCENARIOS:
        result = (await harness.run(scenario)).to_dict()
        validate_m4a_conformance_result(result)
        results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        parser.error("--source-sha must be a full 40-character Git SHA")
    results = asyncio.run(run(args.source_sha))
    document = {
        "schema_version": "1.0",
        "kit": "m4a-fake-conformance-v1",
        "source_sha": args.source_sha,
        "result_count": len(results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result_count": len(results), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
