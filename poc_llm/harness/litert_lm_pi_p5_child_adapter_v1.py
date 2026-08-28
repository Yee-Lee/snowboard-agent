#!/usr/bin/env python3
"""Gate 2A P5 child: continuous real-model chunks under one protocol timer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.litert_lm_child_adapter import (
    BackendFailure,
    Cancelled,
    Child,
    Generation,
    _text_content,
)
from poc_llm.harness.litert_lm_pi_child_adapter import PiChild
from poc_llm.harness.litert_lm_pi_child_adapter_v2 import load_pi_config_v2
from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import protocol_validator


def event(name: str, **fields: int) -> None:
    suffix = "".join(f" {key}={value}" for key, value in fields.items())
    print(
        f"P5_EVENT {name}{suffix} monotonic_ns={time.monotonic_ns()}",
        file=sys.stderr,
        flush=True,
    )


class LiteRtContinuousBackend:
    """The first request repeats chunks; later requests are one-shot health probes."""

    def __init__(self, config: dict[str, Any]):
        import litert_lm

        self._engine = litert_lm.Engine(
            config["model_path"],
            backend=litert_lm.Backend.CPU(thread_count=config["threads"]),
            enable_benchmark=True,
            max_num_tokens=config["engine_max_num_tokens"],
        )
        self._sampler = litert_lm.SamplerConfig(
            temperature=config["temperature"], top_p=config["top_p"]
        )
        self._lock = threading.Lock()
        self._conversation: Any | None = None
        self._cancel_requested = False
        self._native_cancel_invoked = False
        self._continuous_claimed = False

    @staticmethod
    def _metrics(conversation: Any) -> dict[str, int | float]:
        benchmark = conversation.get_benchmark_info()
        return {
            "init_ms": benchmark.init_time_in_second * 1000,
            "ttft_ms": benchmark.time_to_first_token_in_second * 1000,
            "prefill_tokens": benchmark.last_prefill_token_count,
            "prefill_tokens_per_second": benchmark.last_prefill_tokens_per_second,
            "decode_tokens": benchmark.last_decode_token_count,
            "decode_tokens_per_second": benchmark.last_decode_tokens_per_second,
            "kv_tokens": conversation.token_count,
        }

    def _chunk(
        self, prompt: str, max_output_tokens: int, ordinal: int
    ) -> Generation:
        try:
            conversation = self._engine.create_conversation(
                sampler_config=self._sampler,
                max_output_tokens=max_output_tokens,
                automatic_tool_calling=False,
            )
        except Exception as error:
            raise BackendFailure("create_conversation", error) from error
        cancel_immediately = False
        with self._lock:
            self._conversation = conversation
            cancel_immediately = self._cancel_requested
            if cancel_immediately and not self._native_cancel_invoked:
                self._native_cancel_invoked = True
        event("chunk_started", ordinal=ordinal)
        if cancel_immediately:
            event("native_cancel_once", ordinal=ordinal)
            conversation.cancel_process()
        chunks: list[str] = []
        try:
            try:
                for chunk in conversation.send_message_async(prompt):
                    text = _text_content(chunk)
                    if text:
                        chunks.append(text)
                with self._lock:
                    cancelled = self._cancel_requested
                if cancelled:
                    raise Cancelled("continuous generation cancelled")
            except Cancelled:
                raise
            except RuntimeError as error:
                if "CANCELLED" in str(error):
                    raise Cancelled("continuous generation cancelled") from error
                raise BackendFailure("send_message_async", error) from error
            except Exception as error:
                raise BackendFailure("send_message_async", error) from error
            try:
                generation = Generation(
                    text="".join(chunks), metrics=self._metrics(conversation)
                )
            except Exception as error:
                raise BackendFailure("benchmark_info", error) from error
            event("chunk_completed", ordinal=ordinal)
            return generation
        finally:
            with self._lock:
                if self._conversation is conversation:
                    self._conversation = None
            conversation.close()
            event("conversation_discarded", ordinal=ordinal)

    def generate(self, prompt: str, *, max_output_tokens: int) -> Generation:
        with self._lock:
            self._cancel_requested = False
            self._native_cancel_invoked = False
            continuous = not self._continuous_claimed
            self._continuous_claimed = True
        if not continuous:
            return self._chunk(prompt, max_output_tokens, 0)
        ordinal = 0
        try:
            while True:
                self._chunk(prompt, max_output_tokens, ordinal)
                ordinal += 1
                with self._lock:
                    if self._cancel_requested:
                        raise Cancelled("continuous generation cancelled")
        except Cancelled:
            event("continuous_terminal_cancelled", ordinal=ordinal)
            raise

    def cancel(self) -> None:
        with self._lock:
            self._cancel_requested = True
            conversation = self._conversation
            should_cancel = conversation is not None and not self._native_cancel_invoked
            if should_cancel:
                self._native_cancel_invoked = True
        if should_cancel:
            event("native_cancel_once")
            conversation.cancel_process()

    def close(self) -> None:
        self.cancel()
        self._engine.close()


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
                raise ValueError("P5 schema identity mismatch")
        config, _receipt = load_pi_config_v2(
            args.config,
            args.config_sha256,
            args.config_schema,
            args.artifact_receipt,
            args.artifact_receipt_sha256,
            args.artifact_receipt_schema,
        )
        backend = LiteRtContinuousBackend(config)
        child: Child = PiChild(config, args.config_sha256, backend, sys.stdout)
        child.protocol = protocol_validator(
            args.protocol_schema, args.prompt_schema, args.response_schema
        )
    except Exception:
        print("P5 adapter startup authentication failed", file=sys.stderr)
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
