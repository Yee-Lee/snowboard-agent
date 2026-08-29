#!/usr/bin/env python3
"""Gate 2B Gemma adapter with a frozen product-JSON instruction boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.litert_lm_child_adapter import Child, LiteRtBackend
from poc_llm.harness.litert_lm_pi_child_adapter import PiChild
from poc_llm.harness.litert_lm_pi_child_adapter_v2 import load_pi_config_v2
from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import protocol_validator


def gate2b_product_prompt(value: dict[str, Any]) -> str:
    """Render one generic schema instruction; it contains no scored Audio fixture."""

    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return (
        "Act as a deterministic action router. Return exactly one JSON object and nothing else. "
        "Use only actions, perceptions, and tools listed in Input capabilities. "
        "For speech use {\"action_kind\":\"speak\",\"action_payload\":{\"text\":\"brief reply\"},"
        "\"next_perceptions\":[\"listen\"]}. Preserve any explicitly requested current session marker "
        "exactly once in speech; never repeat a trap or earlier marker. "
        "For a tool use {\"action_kind\":\"tool\",\"action_payload\":{\"name\":\"allowed.name\","
        "\"arguments\":{}},\"next_perceptions\":[\"listen\"]}. "
        "When no action is needed use {\"action_kind\":\"rest\",\"action_payload\":{},"
        "\"next_perceptions\":[]}. Do not add markdown or commentary. Input: " + payload
    )


class Gate2BChild(PiChild):
    """Use the Gate 2B prompt without changing the accepted Gate 1/2A adapters."""

    def _generate(self, request_id: str, value: dict[str, Any]) -> None:
        generation = None
        error = None
        try:
            generation = self.backend.generate(
                gate2b_product_prompt(value),
                max_output_tokens=self.config["max_output_tokens"],
            )
        except Exception as caught:  # Sanitized by the inherited protocol boundary.
            error = caught
        self._terminal(request_id, generation, error)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--config-schema", type=Path, required=True)
    parser.add_argument("--config-schema-sha256", required=True)
    parser.add_argument("--protocol-schema", type=Path, required=True)
    parser.add_argument("--protocol-schema-sha256", required=True)
    parser.add_argument("--prompt-schema", type=Path, required=True)
    parser.add_argument("--prompt-schema-sha256", required=True)
    parser.add_argument("--response-schema", type=Path, required=True)
    parser.add_argument("--response-schema-sha256", required=True)
    parser.add_argument("--artifact-receipt", type=Path, required=True)
    parser.add_argument("--artifact-receipt-sha256", required=True)
    parser.add_argument("--artifact-receipt-schema", type=Path, required=True)
    parser.add_argument("--artifact-receipt-schema-sha256", required=True)
    args = parser.parse_args()
    try:
        for path, expected in (
            (args.config_schema, args.config_schema_sha256),
            (args.protocol_schema, args.protocol_schema_sha256),
            (args.prompt_schema, args.prompt_schema_sha256),
            (args.response_schema, args.response_schema_sha256),
            (args.artifact_receipt_schema, args.artifact_receipt_schema_sha256),
        ):
            if not path.is_file() or streaming_digest(path) != expected:
                raise ValueError("Pi schema identity mismatch")
        config, _receipt = load_pi_config_v2(
            args.config,
            args.config_sha256,
            args.config_schema,
            args.artifact_receipt,
            args.artifact_receipt_sha256,
            args.artifact_receipt_schema,
        )
        backend = LiteRtBackend(config)
        child: Child = Gate2BChild(config, args.config_sha256, backend, sys.stdout)
        child.protocol = protocol_validator(
            args.protocol_schema,
            args.prompt_schema,
            args.response_schema,
        )
    except Exception:
        print("Gate 2B adapter startup authentication failed", file=sys.stderr)
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
