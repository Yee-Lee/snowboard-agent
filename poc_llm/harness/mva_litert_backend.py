"""LiteRT-LM 0.16 M4B-MVA session backend.

This module owns no product composition. It is a POC measurement adapter that keeps one
Conversation per product session, uses the compact text/end constraint, and discards any
Conversation whose runtime state may be dirty.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import threading
import time
from typing import Any

from poc_llm.harness.litert_lm_child_adapter import _text_content
from poc_llm.harness.mva_contract import (
    ContractViolation,
    SESSION_FACTS,
    admit_tokens,
    render_user_turn,
    validate_semantic,
    validate_session_facts,
)


class MvaBackendError(RuntimeError):
    """A sanitized typed backend outcome."""

    def __init__(self, code: str, *, dirty: bool):
        super().__init__(code)
        self.code = code
        self.dirty = dirty


@dataclass(frozen=True)
class MvaGeneration:
    semantic: dict[str, object]
    metrics: dict[str, int | float | None]


class MvaLiteRtBackend:
    """One Engine with at most one active product Conversation."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        system_message: str,
        user_template: str,
        semantic_schema: dict[str, Any],
        litert_lm_module: Any | None = None,
        engine: Any | None = None,
    ) -> None:
        if litert_lm_module is None:
            import litert_lm as litert_lm_module  # type: ignore[no-redef]

        self._litert_lm = litert_lm_module
        self._config = config
        self._system_message = system_message
        self._user_template = user_template
        self._semantic_schema = semantic_schema
        self._sampler = litert_lm_module.SamplerConfig(
            temperature=config["temperature"], top_p=config["top_p"]
        )
        if engine is None:
            engine = litert_lm_module.Engine(
                config["model_path"],
                backend=litert_lm_module.Backend.CPU(thread_count=config["threads"]),
                enable_benchmark=True,
                max_num_tokens=config["engine_kv_tokens"],
            )
        self._engine = engine
        self._conversation: Any | None = None
        self._session_id: str | None = None
        self._last_turn_id = 0
        self._generation_active = False
        self._cancel_called = False
        self._lock = threading.Lock()

    @classmethod
    def from_paths(
        cls,
        config: dict[str, Any],
        *,
        system_prompt_path: Path,
        user_template_path: Path,
        semantic_schema_path: Path,
        litert_lm_module: Any | None = None,
        engine: Any | None = None,
    ) -> "MvaLiteRtBackend":
        return cls(
            config,
            system_message=system_prompt_path.read_text(encoding="utf-8").rstrip("\n"),
            user_template=user_template_path.read_text(encoding="utf-8").rstrip("\n"),
            semantic_schema=json.loads(semantic_schema_path.read_text(encoding="utf-8")),
            litert_lm_module=litert_lm_module,
            engine=engine,
        )

    @property
    def session_id(self) -> str | None:
        with self._lock:
            return self._session_id

    def _new_conversation(self) -> Any:
        return self._engine.create_conversation(
            system_message=self._system_message,
            sampler_config=self._sampler,
            max_output_tokens=self._config["maximum_output_tokens"],
            automatic_tool_calling=False,
            constrained_decoding_config=self._litert_lm.ConstrainedDecodingConfig(
                enable=True,
                provider=self._litert_lm.LiteRtLmConstraintProviderType.LL_GUIDANCE,
            ),
        )

    def open_session(self, session_id: str, facts: object) -> dict[str, int | float]:
        validate_session_facts(facts)
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            raise ContractViolation("invalid session identity")
        with self._lock:
            if self._conversation is not None or self._session_id is not None:
                raise MvaBackendError("SESSION_MISMATCH", dirty=False)
        start = time.monotonic_ns()
        conversation = None
        try:
            conversation = self._new_conversation()
            initial_kv = conversation.token_count
        except Exception as error:
            if conversation is not None:
                conversation.close()
            raise MvaBackendError("GENERATION_FAILED", dirty=False) from error
        with self._lock:
            self._conversation = conversation
            self._session_id = session_id
            self._last_turn_id = 0
            self._generation_active = False
            self._cancel_called = False
        return {
            "open_ms": (time.monotonic_ns() - start) / 1_000_000,
            "initial_kv_tokens": initial_kv,
        }

    def _require_session(self, session_id: str, turn_id: int) -> Any:
        with self._lock:
            if self._session_id != session_id or self._conversation is None:
                raise MvaBackendError("SESSION_MISMATCH", dirty=False)
            if self._generation_active:
                raise MvaBackendError("BUSY", dirty=False)
            if not isinstance(turn_id, int) or isinstance(turn_id, bool) or turn_id != self._last_turn_id + 1:
                raise MvaBackendError("INVALID_REQUEST", dirty=False)
            self._generation_active = True
            return self._conversation

    def _clear_generation_active(self) -> None:
        with self._lock:
            self._generation_active = False

    def generate(self, session_id: str, turn_id: int, user_text: str) -> MvaGeneration:
        conversation = self._require_session(session_id, turn_id)
        try:
            prompt = render_user_turn(self._user_template, user_text)
            new_user_tokens = len(self._engine.tokenize(user_text))
            current_kv_tokens = conversation.token_count
            rendered = conversation.render_message_to_string(prompt)
            rendered_tokens = len(self._engine.tokenize(rendered))
            admit_tokens(
                new_user_tokens=new_user_tokens,
                incremental_tokens=rendered_tokens,
                current_kv_tokens=current_kv_tokens,
                output_reserve_tokens=self._config["maximum_output_tokens"],
                user_new_limit=self._config["user_new_token_admission"],
                engine_kv_limit=self._config["engine_kv_tokens"],
            )
        except ContractViolation as error:
            if str(error) == "CONTEXT_LIMIT":
                self._discard_session()
                raise MvaBackendError("CONTEXT_LIMIT", dirty=False) from error
            if str(error) == "INPUT_TOO_LARGE":
                self._clear_generation_active()
                raise MvaBackendError("INPUT_TOO_LARGE", dirty=False) from error
            self._clear_generation_active()
            raise MvaBackendError("INVALID_REQUEST", dirty=False) from error
        except Exception as error:
            self._clear_generation_active()
            raise MvaBackendError("GENERATION_FAILED", dirty=False) from error

        started = time.monotonic_ns()
        chunks: list[str] = []
        try:
            response_format = self._litert_lm.ResponseFormat.json(self._semantic_schema)
            for chunk in conversation.send_message_async(prompt, response_format=response_format):
                text = _text_content(chunk)
                if text:
                    chunks.append(text)
            with self._lock:
                cancelled = self._cancel_called
            if cancelled:
                raise MvaBackendError("CANCELLED", dirty=True)
            semantic = validate_semantic(json.loads("".join(chunks)))
            benchmark = conversation.get_benchmark_info()
            kv_tokens = conversation.token_count
            ttc_ms = (time.monotonic_ns() - started) / 1_000_000
            metrics: dict[str, int | float | None] = {
                "ttft_ms": benchmark.time_to_first_token_in_second * 1000,
                "ttc_ms": ttc_ms,
                "new_user_tokens": new_user_tokens,
                "rendered_tokens": rendered_tokens,
                "incremental_tokens": benchmark.last_prefill_token_count,
                "output_tokens": benchmark.last_decode_token_count,
                "kv_tokens": kv_tokens,
            }
        except Exception as error:
            with self._lock:
                cancelled = self._cancel_called
            self._discard_session()
            if cancelled or (isinstance(error, RuntimeError) and "CANCELLED" in str(error)):
                code = "CANCELLED"
            elif isinstance(error, MvaBackendError):
                code = error.code
            elif isinstance(error, (json.JSONDecodeError, ContractViolation)):
                code = "INVALID_OUTPUT"
            else:
                code = "GENERATION_FAILED"
            raise MvaBackendError(code, dirty=True) from error
        with self._lock:
            if self._conversation is not conversation or self._session_id != session_id:
                raise MvaBackendError("PROTOCOL_ERROR", dirty=True)
            self._last_turn_id = turn_id
            self._generation_active = False
        return MvaGeneration(semantic=semantic, metrics=metrics)

    def prewarm_once(self, public_text: str) -> dict[str, int | float | None]:
        """Run one disposable public inference without publishing a product session."""

        with self._lock:
            if self._conversation is not None or self._session_id is not None:
                raise MvaBackendError("BUSY", dirty=False)
        conversation = self._new_conversation()
        try:
            prompt = render_user_turn(self._user_template, public_text)
            response_format = self._litert_lm.ResponseFormat.json(self._semantic_schema)
            started = time.monotonic_ns()
            chunks = [
                text
                for chunk in conversation.send_message_async(prompt, response_format=response_format)
                if (text := _text_content(chunk))
            ]
            validate_semantic(json.loads("".join(chunks)))
            benchmark = conversation.get_benchmark_info()
            return {
                "ttft_ms": benchmark.time_to_first_token_in_second * 1000,
                "ttc_ms": (time.monotonic_ns() - started) / 1_000_000,
                "output_tokens": benchmark.last_decode_token_count,
                "kv_tokens": conversation.token_count,
            }
        except Exception as error:
            raise MvaBackendError("GENERATION_FAILED", dirty=True) from error
        finally:
            conversation.close()

    def cancel(self) -> None:
        """Cancel at most once; the active Conversation must subsequently be discarded."""

        with self._lock:
            conversation = self._conversation
            if conversation is None or not self._generation_active or self._cancel_called:
                return
            self._cancel_called = True
        conversation.cancel_process()

    def close_session(self, session_id: str) -> dict[str, float]:
        with self._lock:
            if session_id != self._session_id or self._conversation is None:
                raise MvaBackendError("SESSION_MISMATCH", dirty=False)
            if self._generation_active:
                raise MvaBackendError("BUSY", dirty=False)
        start = time.monotonic_ns()
        self._discard_session()
        return {"close_ms": (time.monotonic_ns() - start) / 1_000_000}

    def _discard_session(self) -> None:
        with self._lock:
            conversation = self._conversation
            self._conversation = None
            self._session_id = None
            self._last_turn_id = 0
            self._generation_active = False
            self._cancel_called = False
        if conversation is not None:
            conversation.close()

    def close(self) -> None:
        self._discard_session()
        self._engine.close()
