#!/usr/bin/env python3
"""Pi-only authenticated adapter; keeps the frozen ARM64 pre-screen adapter unchanged."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.litert_lm_child_adapter import Child, LiteRtBackend, digest
from poc_llm.harness.pi_runtime import protocol_validator


class PiChild(Child):
    """Adds only the locked Pi PING/PONG frame to the inherited child protocol."""

    def handle(self, frame: dict[str, Any]) -> bool:
        errors = list(self.protocol.iter_errors(frame))
        if not errors and frame.get("type") == "PING":
            self.emit({"type": "PONG", "protocol_version": "snowboard.llm/1", "state": "READY"})
            return True
        return super().handle(frame)


def load_pi_config(path: Path, expected_sha256: str, schema_path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not schema_path.is_file() or digest(path) != expected_sha256:
        raise ValueError("Pi config identity mismatch")
    config = json.loads(path.read_text(encoding="utf-8"))
    if list(Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).iter_errors(config)):
        raise ValueError("Pi strict config schema mismatch")
    for key, sha_key in (("runtime_path", "runtime_sha256"), ("model_path", "model_sha256")):
        artifact = Path(config[key])
        if not artifact.is_absolute() or artifact.resolve() != artifact or digest(artifact) != config[sha_key]:
            raise ValueError(f"{key} identity mismatch")
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--config-schema", type=Path, required=True)
    parser.add_argument("--config-schema-sha256", required=True)
    parser.add_argument("--protocol-schema", type=Path, required=True)
    parser.add_argument("--protocol-schema-sha256", required=True)
    args = parser.parse_args()
    try:
        if (not args.config_schema.is_file() or digest(args.config_schema) != args.config_schema_sha256
                or not args.protocol_schema.is_file() or digest(args.protocol_schema) != args.protocol_schema_sha256):
            raise ValueError("Pi schema identity mismatch")
        config = load_pi_config(args.config, args.config_sha256, args.config_schema)
        backend = LiteRtBackend(config)
        child = PiChild(config, args.config_sha256, backend, sys.stdout)
        child.protocol = protocol_validator(
            args.protocol_schema,
            ROOT / "poc_llm/contracts/m1/prompt-input.schema.json",
            ROOT / "poc_llm/contracts/m1/response.schema.json",
        )
    except Exception:
        print("Pi adapter startup authentication failed", file=sys.stderr)
        return 2
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
