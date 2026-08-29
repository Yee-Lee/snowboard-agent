#!/usr/bin/env python3
"""Gate 2B adapter with enforced input budget and inference-ready pre-warm."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.litert_lm_child_adapter import (
    BackendFailure,
    Cancelled,
    Child,
    Generation,
    LiteRtBackend,
    _text_content,
)
from poc_llm.harness.litert_lm_pi_child_adapter import PiChild
from poc_llm.harness.litert_lm_pi_child_adapter_v2 import load_pi_config_v2
from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import protocol_validator


GATE2B_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action_kind", "action_payload", "next_perceptions"],
    "properties": {
        "action_kind": {"type": "string", "enum": ["speak"]},
        "action_payload": {
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {"text": {"type": "string", "minLength": 1}},
        },
        "next_perceptions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 1,
            "items": {"type": "string", "enum": ["listen"]},
        },
    },
}

PREWARM_VALUE = {
    "perceptions": [{
        "kind": "listen",
        "status": "ok",
        "text": "USER=Say ready.\nINCLUDE=G2BW0000\nOMIT=G2BX0000",
    }],
    "pending_message_count": 0,
    "capabilities": {
        "perceptions": ["listen"],
        "actions": ["speak"],
        "tools": [],
    },
}


class InputBudgetExceeded(RuntimeError):
    """The chat-template-rendered product input exceeds its locked budget."""


class Gate2BLiteRtBackend(LiteRtBackend):
    """Gate 2B-only budgeted constrained backend; historical adapters stay frozen."""

    def __init__(self, config: dict[str, Any]):
        import litert_lm

        self._gate2b_litert_lm = litert_lm
        super().__init__(config)

    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        max_input_tokens: int,
        response_schema: dict[str, Any],
    ) -> Generation:
        litert_lm = self._gate2b_litert_lm
        try:
            conversation = self._engine.create_conversation(
                sampler_config=self._sampler,
                max_output_tokens=max_output_tokens,
                automatic_tool_calling=False,
                constrained_decoding_config=litert_lm.ConstrainedDecodingConfig(
                    enable=True,
                    provider=litert_lm.LiteRtLmConstraintProviderType.LL_GUIDANCE,
                ),
            )
        except Exception as error:
            raise BackendFailure("create_conversation", error) from error
        with self._lock:
            self._conversation = conversation
        try:
            try:
                rendered = conversation.render_message_to_string(prompt)
                rendered_tokens = len(self._engine.tokenize(rendered))
            except Exception as error:
                raise BackendFailure("input_tokenize", error) from error
            if rendered_tokens > max_input_tokens:
                raise InputBudgetExceeded("rendered input token budget exceeded")
            try:
                text = _text_content(conversation.send_message(
                    prompt,
                    response_format=litert_lm.ResponseFormat.json(response_schema),
                ))
            except RuntimeError as error:
                if "CANCELLED" in str(error):
                    raise Cancelled("generation cancelled") from error
                raise BackendFailure("send_message", error) from error
            except Exception as error:
                raise BackendFailure("send_message", error) from error
            try:
                benchmark = conversation.get_benchmark_info()
                metrics = {
                    "init_ms": benchmark.init_time_in_second * 1000,
                    "ttft_ms": benchmark.time_to_first_token_in_second * 1000,
                    "prefill_tokens": benchmark.last_prefill_token_count,
                    "prefill_tokens_per_second": benchmark.last_prefill_tokens_per_second,
                    "decode_tokens": benchmark.last_decode_token_count,
                    "decode_tokens_per_second": benchmark.last_decode_tokens_per_second,
                    "kv_tokens": conversation.token_count,
                }
            except Exception as error:
                raise BackendFailure("benchmark_info", error) from error
            if metrics["prefill_tokens"] > max_input_tokens:
                raise InputBudgetExceeded("runtime prefill token budget exceeded")
            return Generation(text=text, metrics=metrics)
        finally:
            with self._lock:
                if self._conversation is conversation:
                    self._conversation = None
            conversation.close()


def _product_text(value: dict[str, Any]) -> str:
    """Accept only the frozen speak/listen product surface and return its input."""

    perceptions = value.get("perceptions")
    capabilities = value.get("capabilities")
    if (
        value.get("pending_message_count") != 0
        or not isinstance(perceptions, list)
        or len(perceptions) != 1
        or perceptions[0].get("kind") != "listen"
        or perceptions[0].get("status") != "ok"
        or not isinstance(perceptions[0].get("text"), str)
        or capabilities != {
            "perceptions": ["listen"],
            "actions": ["speak"],
            "tools": [],
        }
    ):
        raise ValueError("Gate 2B product input profile mismatch")
    return perceptions[0]["text"]


def gate2b_product_prompt(value: dict[str, Any]) -> str:
    """Render the compact, generic instruction used by pre-warm and scoring."""

    return (
        "Return JSON only. Briefly answer USER in speech. Copy INCLUDE exactly once "
        "into text. Never copy OMIT. Keep next_perceptions as listen.\n"
        + _product_text(value)
    )


class Gate2BChild(PiChild):
    """Apply Gate 2B budget and structured-output constraints to every request."""

    def _generate(self, request_id: str, value: dict[str, Any]) -> None:
        generation = None
        error = None
        try:
            generation = self.backend.generate(
                gate2b_product_prompt(value),
                max_output_tokens=self.config["max_output_tokens"],
                max_input_tokens=self.config["max_input_tokens"],
                response_schema=GATE2B_RESPONSE_SCHEMA,
            )
        except Exception as caught:  # Sanitized by the inherited protocol boundary.
            error = caught
        self._terminal(request_id, generation, error)


def prewarm(backend: Gate2BLiteRtBackend, config: dict[str, Any]) -> dict[str, int | float | str]:
    """Complete one fixed public inference before publishing protocol READY."""

    prompt = gate2b_product_prompt(PREWARM_VALUE)
    generation = backend.generate(
        prompt,
        max_output_tokens=config["max_output_tokens"],
        max_input_tokens=config["max_input_tokens"],
        response_schema=GATE2B_RESPONSE_SCHEMA,
    )
    if generation.metrics.get("decode_tokens", 0) <= 0:
        raise RuntimeError("Gate 2B pre-warm produced no decode tokens")
    return {
        "event": "INFERENCE_READY",
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        **generation.metrics,
    }


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
    backend: Gate2BLiteRtBackend | None = None
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
        backend = Gate2BLiteRtBackend(config)
        prewarm_metrics = prewarm(backend, config)
        child: Child = Gate2BChild(config, args.config_sha256, backend, sys.stdout)
        child.protocol = protocol_validator(
            args.protocol_schema,
            args.prompt_schema,
            args.response_schema,
        )
    except Exception:
        if backend is not None:
            backend.close()
        print("Gate 2B adapter startup/pre-warm failed", file=sys.stderr)
        return 2
    print(
        "PREWARM_DIAGNOSTIC "
        + json.dumps(prewarm_metrics, sort_keys=True, separators=(",", ":")),
        file=sys.stderr,
        flush=True,
    )
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
