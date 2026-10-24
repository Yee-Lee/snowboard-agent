"""Record a current-run M3 manual observation without pre-filling PASS."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("test_id", choices=("M3-AUDI-003", "M3-DSPI-002", "M3-DSPI-005"))
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--media", action="append", default=[])
    parser.add_argument("checks", nargs="+")
    args = parser.parse_args()
    parsed: dict[str, bool] = {}
    for item in args.checks:
        name, separator, raw = item.partition("=")
        if not separator or raw.lower() not in {"pass", "fail"}:
            parser.error("checks must use name=pass or name=fail")
        parsed[name] = raw.lower() == "pass"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / f"{args.test_id}.json"
    target.write_text(json.dumps({
        "test_id": args.test_id,
        "operator": args.operator,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": parsed,
        "media_metadata": args.media,
    }, indent=2, sort_keys=True) + "\n")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
