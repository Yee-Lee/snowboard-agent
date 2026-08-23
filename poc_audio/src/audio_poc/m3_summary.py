"""Build a complete, sanitized draft index for one M3 hardware run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m3_authorization import (
    PUBLICATION_STATUS,
    load_signoff,
    validate_formal_authorization,
    validate_m3_result,
)
from .m3_packet import CAPTURE_CASES, PACKET_ID, load_packet, validate_repo_inputs


EXPECTED_TEST_IDS = {
    "M3-PREFLIGHT-01",
    *(item[0] for item in CAPTURE_CASES),
    "M3-PCM-01",
    *(f"M3-LIFE-{index:02d}" for index in range(1, 7)),
    "M3-TTS-SET-01",
    "M3-ASR-DIRECT-PCM-BASELINE-001",
    "M3-VAD-SET-01",
    "M3-ASR-HAL-PATH-001",
}
OFFLINE_PHASES = {"tts", "asr-direct", "asr-hal", "vad-hal", "candidate-lifecycle"}


def build_summary(
    result_dir: Path,
    signoff: dict[str, Any],
) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    for path in sorted(result_dir.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and document.get("packet_id") == PACKET_ID:
            validate_m3_result(document)
            documents.append(document)
    observed = [item["test_id"] for item in documents]
    duplicates = sorted(name for name, count in Counter(observed).items() if count != 1)
    missing = sorted(EXPECTED_TEST_IDS - set(observed))
    unexpected = sorted(set(observed) - EXPECTED_TEST_IDS)
    if duplicates or missing or unexpected:
        raise ValueError(
            f"M3 result set mismatch: duplicates={duplicates} missing={missing} "
            f"unexpected={unexpected}"
        )
    if any(
        item["poc_execution_sha"] != signoff["poc_execution_sha"]
        or item["core_execution_sha"] != signoff["core_execution_sha"]
        for item in documents
    ):
        raise ValueError("M3 result set contains mixed execution SHAs")
    for item in documents:
        if item.get("phase") in OFFLINE_PHASES:
            network = item.get("details", {}).get("network", {})
            if network.get("network_disabled") is not True:
                raise ValueError(f"M3 offline proof is missing for {item['test_id']}")
    by_id = {item["test_id"]: item for item in documents}
    direct_lock = by_id["M3-ASR-DIRECT-PCM-BASELINE-001"]["details"].get(
        "fixture_lock_sha256"
    )
    hal_lock = by_id["M3-ASR-HAL-PATH-001"]["details"].get("fixture_lock_sha256")
    if not direct_lock or direct_lock != hal_lock:
        raise ValueError("M3 paired ASR paths do not bind the same source fixture lock")
    counts = Counter(item["result"] for item in documents)
    proposed = "FAIL" if counts["FAIL"] else (
        "INCONCLUSIVE" if counts["INCONCLUSIVE"] else "PASS"
    )
    return {
        "schema_version": "1.0",
        "summary_id": "M3-RISK-FOCUSED-QUALIFICATION-DRAFT-001",
        "packet_id": PACKET_ID,
        "publication_status": PUBLICATION_STATUS,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_execution_sha": signoff["poc_execution_sha"],
        "core_execution_sha": signoff["core_execution_sha"],
        "result_count": len(documents),
        "result_counts": {name: counts[name] for name in ("PASS", "FAIL", "INCONCLUSIVE")},
        "proposed_disposition": proposed,
        "test_ids": sorted(observed),
        "offline_inference_phases": sorted(OFFLINE_PHASES),
        "paired_asr_source_fixture_lock_sha256": direct_lock,
        "decision_boundary": (
            "DRAFT ONLY; User confirmation is required before publication, candidate "
            "selection, fallback activation, M3.1 activation or gate status change."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--signoff", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("M3 summary output must be a new path")
    packet = load_packet(args.packet)
    validate_repo_inputs(packet, args.repo_root)
    signoff = load_signoff(args.signoff)
    validate_formal_authorization(
        signoff, args.packet, args.repo_root, args.core_root,
    )
    summary = build_summary(args.result_dir, signoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(summary, destination, indent=2, sort_keys=True)
        destination.write("\n")
    print(json.dumps({
        "summary": str(args.output),
        "proposed_disposition": summary["proposed_disposition"],
        "publication_status": summary["publication_status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
