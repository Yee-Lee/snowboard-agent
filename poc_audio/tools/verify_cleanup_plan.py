#!/usr/bin/env python3
"""Verify cleanup receipts and print eligible logical locators; never delete."""

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--conditions", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    receipts = {row["bundle_id"]: row for row in json.loads(args.receipts.read_text())["bundles"]}
    conditions = set(json.loads(args.conditions.read_text())["satisfied"])
    eligible = []
    for row in manifest["entries"]:
        if not row["delete_after_verified_receipt"] or row["active_references"]:
            continue
        receipt = receipts.get(row["archive_bundle_id"])
        expected_hash = row["required_local_receipt_hash"]
        expected_size = row["required_local_receipt_size"]
        if (
            receipt
            and isinstance(expected_hash, str)
            and re.fullmatch(r"[0-9a-f]{64}", expected_hash)
            and isinstance(expected_size, int)
            and expected_size > 0
            and expected_hash == receipt.get("archive_sha256")
            and expected_size == receipt.get("archive_bytes")
            and set(row["preflight_conditions"]).issubset(conditions)
        ):
            eligible.append(row["locator"])
    print(json.dumps({"schema_version": 1, "dry_run": True, "eligible": eligible}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
