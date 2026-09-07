"""LiteRT-LM backend for the isolated M4B-MVA efficiency experiment."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
import time
from typing import Any, Callable

from poc_llm.efficiency.raw_stream import RawStreamError, send_message_raw
from poc_llm.efficiency.readiness import ConversationReadinessPool, ReadinessIdentity
from poc_llm.efficiency.streaming import consume_raw_stream, response_format
from poc_llm.harness.mva_contract import (
    ContractViolation,
    admit_tokens,
    render_user_turn,
    validate_session_facts,
)
from poc_llm.harness.mva_litert_backend import MvaBackendError, MvaGeneration
from poc_llm.harness.mva_surface import canonical_bytes


@dataclass(frozen=True)
class PreparedConversation:
    open_ms: float
    initial_kv_tokens: int
    held_at_monotonic: float


class EfficiencyLiteRtBackend:
    """One Engine with a single direct or clean-held Conversation."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        encoding: str,
        system_message: str,
        user_template: str,
        semantic_schema: dict[str, Any],
        profile_digest: str,
        child_generation: int,
        litert_lm_module: Any | None = None,
        engine: Any | None = None,
        raw_sender: Callable[..., Any] = send_message_raw,
        clock: Callable[[], float] = time.monotonic,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if encoding not in {"J", "P"}:
            raise ValueError("encoding must be J or P")
        if litert_lm_module is None:
            import litert_lm as litert_lm_module  # type: ignore[no-redef]
        self._litert_lm = litert_lm_module
        self._config = config
        self._encoding = encoding
        self._system_message = system_message
        self._user_template = user_template
        self._semantic_schema = semantic_schema
        self._profile_digest = profile_digest
        self._child_generation = child_generation
        self._raw_sender = raw_sender
        self._clock = clock
        self._clock_ns = clock_ns
        self._sampler = litert_lm_module.SamplerConfig(
            temperature=config["temperature"], top_p=config["top_p"]
        )
        if engine is None:
            engine = litert_lm_module.Engine(
                config["model_path"],
                backend=litert_lm_module.Backend.CPU(thread_count=config["threads"]),
                cache_dir=config["cache_dir"],
                enable_benchmark=True,
                max_num_tokens=config["engine_kv_tokens"],
            )
        self._engine = engine
        self._pool = ConversationReadinessPool(self._close_conversation, hold_seconds=30.0)
        self._conversation: Any | None = None
        self._conversation_from_hold = False
        self._session_id: str | None = None
        self._last_turn_id = 0
        self._generation_active = False
        self._cancel_called = False
        self._lock = threading.Lock()

    @property
    def session_id(self) -> str | None:
        with self._lock:
            return self._session_id

    @property
    def readiness_state(self) -> str:
        return self._pool.state

    def _identity(self, facts: object) -> ReadinessIdentity:
        facts_digest = hashlib.sha256(canonical_bytes(facts)).hexdigest()
        return ReadinessIdentity(facts_digest, self._profile_digest, self._child_generation)

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

    @staticmethod
    def _close_conversation(conversation: Any) -> None:
        conversation.close()

    def prepare_clean(self, facts: object) -> PreparedConversation:
        validate_session_facts(facts)
        with self._lock:
            if self._conversation is not None or self._session_id is not None:
                raise MvaBackendError("BUSY", dirty=False)
        ticket = self._pool.begin_open(self._identity(facts), facts)
        start_ns = self._clock_ns()
        conversation = None
        try:
            conversation = self._new_conversation()
            initial_kv = conversation.token_count
            held_at = self._clock()
            if not self._pool.finish_open(ticket, conversation, now=held_at):
                raise MvaBackendError("CANCELLED", dirty=False)
        except MvaBackendError:
            raise
        except Exception as error:
            if conversation is not None and self._pool.state == "OPENING":
                conversation.close()
            self._pool.cancel_open()
            raise MvaBackendError("GENERATION_FAILED", dirty=False) from error
        return PreparedConversation(
            open_ms=(self._clock_ns() - start_ns) / 1_000_000,
            initial_kv_tokens=initial_kv,
            held_at_monotonic=held_at,
        )

    def cancel_prepare(self) -> bool:
        return self._pool.cancel_open()

    def close_unclaimed(self) -> bool:
        return self._pool.close_unclaimed()

    def open_session(
        self,
        session_id: str,
        facts: object,
        *,
        readiness: str = "D",
        allow_fallback: bool = False,
    ) -> dict[str, int | float | bool | str]:
        validate_session_facts(facts)
        if readiness not in {"D", "H"}:
            raise ContractViolation("readiness must be D or H")
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            raise ContractViolation("invalid session identity")
        with self._lock:
            if self._conversation is not None or self._session_id is not None:
                raise MvaBackendError("SESSION_MISMATCH", dirty=False)
        start_ns = self._clock_ns()
        conversation = None
        adopted = False
        mode = readiness
        try:
            if readiness == "H":
                conversation = self._pool.adopt(self._identity(facts), now=self._clock())
                adopted = conversation is not None
                if not adopted and not allow_fallback:
                    raise MvaBackendError("READINESS_MISMATCH", dirty=False)
                if not adopted:
                    mode = "FALLBACK_D"
            if conversation is None:
                if self._pool.live_count:
                    raise MvaBackendError("BUSY", dirty=False)
                conversation = self._new_conversation()
            initial_kv = conversation.token_count
        except MvaBackendError:
            raise
        except Exception as error:
            if conversation is not None:
                conversation.close()
            raise MvaBackendError("GENERATION_FAILED", dirty=False) from error
        with self._lock:
            self._conversation = conversation
            self._conversation_from_hold = adopted
            self._session_id = session_id
            self._last_turn_id = 0
            self._generation_active = False
            self._cancel_called = False
        return {
            "open_ms": (self._clock_ns() - start_ns) / 1_000_000,
            "initial_kv_tokens": initial_kv,
            "held_adopted": adopted,
            "readiness_mode": mode,
        }

    def _require_session(self, session_id: str, turn_id: int) -> Any:
        with self._lock:
            if self._session_id != session_id or self._conversation is None:
                raise MvaBackendError("SESSION_MISMATCH", dirty=False)
            if self._generation_active:
                raise MvaBackendError("BUSY", dirty=False)
            if (not isinstance(turn_id, int) or isinstance(turn_id, bool)
                    or turn_id != self._last_turn_id + 1):
                raise MvaBackendError("INVALID_REQUEST", dirty=False)
            self._generation_active = True
            return self._conversation

    def generate(
        self,
        session_id: str,
        turn_id: int,
        user_text: str,
        *,
        on_provisional_text: Callable[[str], None] | None = None,
    ) -> MvaGeneration:
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
            with self._lock:
                self._generation_active = False
            code = "INPUT_TOO_LARGE" if str(error) == "INPUT_TOO_LARGE" else "INVALID_REQUEST"
            raise MvaBackendError(code, dirty=False) from error
        except Exception as error:
            with self._lock:
                self._generation_active = False
            raise MvaBackendError("GENERATION_FAILED", dirty=False) from error

        started_ns = self._clock_ns()
        try:
            selected_format = response_format(self._litert_lm, self._encoding, self._semantic_schema)
            chunks = self._raw_sender(conversation, prompt, response_format=selected_format)
            stream = consume_raw_stream(
                chunks,
                encoding=self._encoding,
                started_ns=started_ns,
                clock_ns=self._clock_ns,
                on_provisional_text=on_provisional_text,
            )
            with self._lock:
                if self._cancel_called:
                    raise MvaBackendError("CANCELLED", dirty=True)
            benchmark = conversation.get_benchmark_info()
            metrics: dict[str, int | float | None] = {
                "ttft_ms": benchmark.time_to_first_token_in_second * 1000,
                "ttc_ms": (self._clock_ns() - started_ns) / 1_000_000,
                "first_decodable_text_ms": stream.first_decodable_text_ms,
                "first_chunk_ms": stream.first_chunk_ms,
                "first_chunk_codepoints": stream.first_chunk_codepoints,
                "new_user_tokens": new_user_tokens,
                "rendered_tokens": rendered_tokens,
                "incremental_tokens": benchmark.last_prefill_token_count,
                "output_tokens": benchmark.last_decode_token_count,
                "kv_tokens": conversation.token_count,
            }
        except Exception as error:
            with self._lock:
                cancelled = self._cancel_called
            self._discard_session()
            if cancelled or (isinstance(error, RawStreamError) and error.code == "CANCELLED"):
                code = "CANCELLED"
            elif isinstance(error, MvaBackendError):
                code = error.code
            elif isinstance(error, (ContractViolation, RawStreamError)):
                code = "INVALID_OUTPUT"
            else:
                code = "GENERATION_FAILED"
            raise MvaBackendError(code, dirty=True) from error
        with self._lock:
            if self._conversation is not conversation or self._session_id != session_id:
                raise MvaBackendError("PROTOCOL_ERROR", dirty=True)
            self._last_turn_id = turn_id
            self._generation_active = False
        return MvaGeneration(semantic=stream.semantic, metrics=metrics)

    def cancel(self) -> None:
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
            conversation = self._conversation
            from_hold = self._conversation_from_hold
        start_ns = self._clock_ns()
        try:
            if from_hold:
                self._pool.release_adopted(conversation)
            else:
                conversation.close()
        except Exception as error:
            self._reset_session()
            raise MvaBackendError("CLEANUP_FAILED", dirty=True) from error
        self._reset_session()
        return {"close_ms": (self._clock_ns() - start_ns) / 1_000_000}

    def _reset_session(self) -> None:
        with self._lock:
            self._conversation = None
            self._conversation_from_hold = False
            self._session_id = None
            self._last_turn_id = 0
            self._generation_active = False
            self._cancel_called = False

    def _discard_session(self) -> None:
        with self._lock:
            conversation = self._conversation
            from_hold = self._conversation_from_hold
        try:
            if conversation is not None:
                if from_hold:
                    self._pool.release_adopted(conversation)
                else:
                    conversation.close()
        finally:
            self._reset_session()

    def close(self) -> None:
        if self.session_id is not None:
            self._discard_session()
        self._pool.close_unclaimed()
        self._engine.close()
