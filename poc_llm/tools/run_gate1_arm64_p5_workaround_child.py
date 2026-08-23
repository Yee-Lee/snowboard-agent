#!/usr/bin/env python3
"""User-approved, non-contract P5 timeout fault-injection child."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.litert_lm_child_adapter import (
    Child, LiteRtBackend, load_authenticated_config,
)

WORKAROUND_TIMEOUT_MS = 1000


def effective_config(base: dict[str, object]) -> dict[str, object]:
    value = dict(base)
    value["generate_timeout_ms"] = WORKAROUND_TIMEOUT_MS
    return value


def config_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--base-config-sha256", required=True)
    args = parser.parse_args()
    try:
        base = load_authenticated_config(
            args.base_config, args.base_config_sha256
        )
        config = effective_config(base)
        backend = LiteRtBackend(config)
    except Exception:
        print("workaround child startup authentication failed", file=sys.stderr)
        return 2
    child = Child(config, config_digest(config), backend, sys.stdout)
    child.ready()
    try:
        for line in sys.stdin:
            try:
                frame = json.loads(line)
            except (json.JSONDecodeError, UnicodeError):
                break
            if not isinstance(frame, dict) or not child.handle(frame):
                break
    finally:
        child.close()
    return 0 if child.closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
