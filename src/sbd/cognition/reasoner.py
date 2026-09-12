"""Reasoner — single cognition module and Ch 9 response normalizer."""

from __future__ import annotations

import asyncio
import logging
import hashlib
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Callable

from sbd.adaptor.errors import AdapterRejected, AdapterTimeout
from sbd.cognition.llm import (LLMEngineAdapter, AdmissionSnapshot, SemanticGeneration,
    LLMFatalError, MemoryAdmissionDenied, ReplaceableGenerationFailure)
from sbd.cognition.llm_child_protocol import (
    ReasoningInputContractError,
    ReasoningInputTooLarge,
    validate_counts,
)
from sbd.cognition.prompt_builder import PromptBuilder, ListenProjector, UnsupportedInputError
from sbd.cognition.semantic import validate_semantic
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, LLMResponse, PerceptionResult
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime


if TYPE_CHECKING:
    from sbd.action.payload_validator import ActionPayloadValidator


logger = logging.getLogger(__name__)
_PERCEPTION_KINDS = ("listen", "read", "look")
_ACTION_KINDS = ("speak", "tool")
_DEFAULT_PERCEPTIONS = ("listen",)
_REASON_TIMEOUT_SECONDS = 30.0
_APOLOGY = "抱歉，我現在無法完成回應，請再試一次。"
_NO_INPUT = "我沒聽清楚，請再說一次。"
_INPUT_LIMIT = "這句有點長，請縮短後再說一次。"
_CONTEXT_LIMIT = "對話內容已滿，請再說一次。"
_MEMORY_NOTICE = "系統需要整理，請稍後再試。"
_REPLACEABLE = "剛才沒有成功，請再說一次。"


class Reasoner(WorkerRuntime):
    """Drive one stateless LLM turn and publish exactly one terminal Fact."""

    def __init__(
        self,
        llm: LLMEngineAdapter,
        prompt_builder: PromptBuilder | ListenProjector,
        bus: EventBus,
        capability_of: Callable[[str], bool],
        action_validator: ActionPayloadValidator,
        reason_timeout_seconds: float = _REASON_TIMEOUT_SECONDS,
        *,
        control: object | None = None,
        observer: object | None = None,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._prompt_builder = prompt_builder
        self._bus = bus
        self._capability_of = capability_of
        self._action_validator = action_validator
        self._reason_timeout_seconds = reason_timeout_seconds
        self._product = isinstance(prompt_builder, ListenProjector)
        self._control = llm.control if self._product else control
        self._observer = observer

    @property
    def control(self) -> object | None:
        return self._control

    async def start(self) -> None:
        await self._llm.start()

    async def stop(self) -> None:
        await self.abort()
        await self._llm.stop()

    async def abort(self) -> None:
        await super().abort()

    async def force_abort(self) -> ForceAbortReport:
        return await super().force_abort()

    async def reason(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        perception_results: tuple[PerceptionResult, ...],
        pending_message_ids: tuple[str, ...],
        *,
        conversation_generation: int,
    ) -> None:
        if self._product:
            operation = self._reason_product(session_id, turn_id, correlation_id,
                perception_results, pending_message_ids, conversation_generation)
            del perception_results, pending_message_ids
            await operation
            return
        async def body() -> None:
            unexpected: Exception | None = None
            response: LLMResponse | None = None
            try:
                value = self._prompt_builder.build(
                    perceptions=perception_results,
                    pending_message_count=len(pending_message_ids),
                    available_perceptions=self._available(_PERCEPTION_KINDS),
                    available_actions=self._available(_ACTION_KINDS),
                )
                try:
                    async with asyncio.timeout(self._reason_timeout_seconds):
                        generation = await self._await_operation(
                            self._llm.generate(value)
                        )
                    response = self._normalize(
                        generation.response,
                        session_id,
                        turn_id,
                        correlation_id,
                    )
                except TimeoutError:
                    await self._llm.abort()
                    response = self._fallback(
                        session_id, turn_id, correlation_id
                    )
                except ReasoningInputContractError:
                    raise
                except (
                    ReasoningInputTooLarge,
                    AdapterRejected,
                    AdapterTimeout,
                    ValueError,
                    TypeError,
                ):
                    response = self._fallback(
                        session_id, turn_id, correlation_id
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                unexpected = exc

            if unexpected is not None:
                await self._bus.publish(
                    ErrorOccurred(
                        where="cognition.reasoner",
                        error="reasoner failed",
                        exception_type=type(unexpected).__name__,
                    )
                )
                raise unexpected
            if response is not None and self._may_publish():
                await self._bus.publish(response)

        await self._run_call(body)

    async def _reason_product(self, session_id, turn_id, correlation_id,
                              perceptions, pending_ids, generation) -> None:
        async def body() -> None:
            nonlocal perceptions, pending_ids
            failure: LLMFatalError | None = None
            response: LLMResponse | None = None
            try:
                if self._observer is not None:
                    self._observer.begin_turn(generation, turn_id)
                async with asyncio.timeout(self._reason_timeout_seconds):
                    # The operation task owns the complete transaction and the
                    # adapter's reentrant lock, including measure and generate.
                    operation = self._product_turn(
                        session_id, turn_id, correlation_id, perceptions,
                        pending_ids, generation)
                    perceptions, pending_ids = (), ()
                    response = await self._await_operation(operation)
            except asyncio.CancelledError:
                if self._observer is not None:
                    try:
                        self._observer.finish("CANCELLED")
                    except Exception:
                        pass  # An observation sink cannot replace cancellation.
                raise
            except UnsupportedInputError:
                failure = LLMFatalError("UNSUPPORTED_INPUT")
            except TimeoutError:
                try:
                    await self._llm.abort()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass
                failure = LLMFatalError("REASONER_TIMEOUT")
            except Exception:
                failure = LLMFatalError("M4B_REASONER_FAILED")
            if failure is not None:
                if self._observer is not None:
                    try:
                        self._observer.outcome("E1")
                        self._observer.finish("FAILED")
                    except Exception:
                        pass  # Preserve the original E1 and its supervision event.
                if self._may_publish():
                    await self._bus.publish(ErrorOccurred(where="cognition.reasoner",
                        error=str(failure), exception_type=type(failure).__name__))
                raise failure from None
            if response is not None and self._may_publish():
                await self._bus.publish(response)

        await self._run_call(body)

    async def _product_turn(self, session_id, turn_id, correlation_id,
                            perceptions, pending_ids, generation) -> LLMResponse:
        async with self._llm.serialized():
            if (type(session_id) is not str or not session_id or
                    type(generation) is not int or generation < 1 or
                    type(turn_id) is not int or turn_id < 0 or type(pending_ids) is not tuple):
                raise UnsupportedInputError()
            if (self._capability_of("listen") is not True or
                    self._capability_of("speak") is not True):
                raise UnsupportedInputError()
            self._llm.assert_conversation(session_id, generation)
            text = self._prompt_builder.project(perceptions=perceptions,
                session_id=session_id, turn_id=turn_id,
                pending_message_count=len(pending_ids),
                available_perceptions=("listen",), available_actions=("speak",))
            del perceptions, pending_ids
            if self._observer is not None:
                self._observer.input_codepoints(None if text is None else len(text))
            identity = (session_id, turn_id, correlation_id)
            if text is None:
                return self._product_fact(_NO_INPUT, "KEEP_NEXT", identity, outcome="R1")
            if len(text) > 20:
                return self._product_fact(_INPUT_LIMIT, "KEEP_NEXT", identity, outcome="R1")
            snapshot = await self._llm.measure(session_id, generation, text)
            if not isinstance(snapshot, AdmissionSnapshot):
                raise LLMFatalError("INVALID_ADMISSION")
            validate_counts({key:getattr(snapshot,key) for key in (
                "user_tokens", "current_kv_tokens", "rendered_incremental_tokens",
                "runtime_prefill_tokens", "output_reserve_tokens", "engine_context_tokens")})
            if (snapshot.session_id != session_id or type(snapshot.generation) is not int or
                    snapshot.generation != generation or type(snapshot.ticket) is not str or
                    re.fullmatch(r"[0-9a-f]{32}", snapshot.ticket) is None or
                    snapshot.input_sha256 != hashlib.sha256(text.encode()).hexdigest()):
                raise LLMFatalError("INVALID_ADMISSION")
            revision = self._llm.conversation_revision
            if type(revision) is not int or revision < 0:
                raise LLMFatalError("INVALID_REVISION")
            if snapshot.user_tokens > 32:
                from sbd.cognition.llm import TicketDiscardProof
                del text
                proof = await self._llm.discard_ticket(snapshot)
                if (not isinstance(proof, TicketDiscardProof) or
                        proof.session_id != snapshot.session_id or
                        type(proof.generation) is not int or proof.generation != snapshot.generation or
                        type(proof.conversation_revision) is not int or proof.conversation_revision != revision or
                        proof.ticket != snapshot.ticket or proof.input_sha256 != snapshot.input_sha256 or
                        proof.native_render_scrubbed is not True or proof.ticket_invalidated is not True or
                        proof.private_input_erased is not True or proof.conversation_state != "ready" or
                        self._llm.conversation_revision != revision):
                    raise LLMFatalError("INVALID_DISCARD_PROOF")
                self._llm.assert_conversation(session_id, generation)
                del snapshot, proof
                return self._product_fact(_INPUT_LIMIT, "KEEP_NEXT", identity, outcome="R1")
            if revision == 0 and snapshot.runtime_prefill_tokens > 128:
                raise LLMFatalError("INVALID_FRESH_PREFILL")
            if (snapshot.current_kv_tokens + snapshot.rendered_incremental_tokens
                    + snapshot.output_reserve_tokens > snapshot.engine_context_tokens):
                return self._product_fact(_CONTEXT_LIMIT, "REPLACE_NEXT", identity, outcome="R2")
            try:
                result = await self._llm.generate(snapshot, text)
            except MemoryAdmissionDenied as denied:
                if type(denied.speak_allowed) is not bool:
                    raise LLMFatalError("INVALID_MEMORY_OUTCOME") from None
                return self._product_fact(_MEMORY_NOTICE if denied.speak_allowed else "",
                                          "END_SESSION", identity,
                                          outcome="NOTICE" if denied.speak_allowed else "SILENT")
            except ReplaceableGenerationFailure as failed:
                if (failed.request_terminal_proven is not True or failed.engine_usable is not True or
                        failed.code not in {"INVALID_SEMANTIC", "GENERATION_REJECTED", "GENERATION_TIMEOUT"}):
                    raise LLMFatalError("INVALID_TERMINAL_PROOF") from None
                return self._product_fact(_REPLACEABLE, "REPLACE_NEXT", identity, outcome="R2")
            if not isinstance(result, SemanticGeneration):
                raise LLMFatalError("INVALID_SEMANTIC_RESULT")
            semantic = validate_semantic({"text":result.text,"end":result.end})
            if (type(result.safe_fragments) is not tuple or
                    any(type(fragment) is not str or not fragment for fragment in result.safe_fragments) or
                    not semantic.text.startswith("".join(result.safe_fragments))):
                raise LLMFatalError("INVALID_SEMANTIC_PREFIX")
            return self._product_fact(semantic.text,
                "END_SESSION" if semantic.end else "KEEP_NEXT", identity)

    def _product_fact(self, text: str, route: str, identity: tuple, *, outcome="GENERATE") -> LLMResponse:
        if self._capability_of("speak") is not True or self._capability_of("listen") is not True:
            raise LLMFatalError("UNSUPPORTED_INPUT")
        kind = "speak" if text else "rest"
        payload = {"text":text} if text else {}
        self._action_validator.validate(kind, payload)
        if self._observer is not None:
            self._observer.outcome(outcome)
        return LLMResponse(action_kind=kind, action_payload=payload,
            post_action_route=route, next_perceptions=() if route == "END_SESSION" else ("listen",),
            session_id=identity[0], turn_id=identity[1], correlation_id=identity[2])

    def _normalize(
        self,
        raw: Mapping[str, object],
        session_id: str,
        turn_id: int,
        correlation_id: int,
    ) -> LLMResponse:
        if type(raw) is not dict or set(raw) != {
            "action_kind",
            "action_payload",
            "next_perceptions",
        }:
            logger.warning(
                "LLM response schema rejected path=$ reason=exact fields"
            )
            raise ValueError("invalid model response")
        action_kind = raw["action_kind"]
        payload = raw["action_payload"]
        requested = raw["next_perceptions"]
        if type(action_kind) is not str or type(payload) is not dict:
            raise ValueError("invalid model response")
        if type(requested) is not list or any(
            type(kind) is not str for kind in requested
        ):
            raise ValueError("invalid model response")
        if len(requested) != len(set(requested)):
            raise ValueError("duplicate next perception")
        self._action_validator.validate(action_kind, payload)
        if action_kind == "rest":
            if requested:
                raise ValueError("rest cannot request a perception")
            return LLMResponse(
                action_kind="rest",
                action_payload={},
                post_action_route="END_SESSION",
                next_perceptions=(),
                session_id=session_id,
                turn_id=turn_id,
                correlation_id=correlation_id,
            )
        if action_kind not in _ACTION_KINDS or not self._capability_of(action_kind):
            raise ValueError("unavailable action")
        if not requested or any(not self._capability_of(kind) for kind in requested):
            raise ValueError("no available next perception")
        next_perceptions = tuple(requested)
        return LLMResponse(
            action_kind=action_kind,  # type: ignore[arg-type]
            action_payload=payload,
            post_action_route="KEEP_NEXT",
            next_perceptions=next_perceptions,
            session_id=session_id,
            turn_id=turn_id,
            correlation_id=correlation_id,
        )

    def _fallback(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
    ) -> LLMResponse:
        next_perceptions = self._dedupe_available(_DEFAULT_PERCEPTIONS)
        if self._capability_of("speak") and next_perceptions:
            payload = {"text": _APOLOGY}
            self._action_validator.validate("speak", payload)
            return LLMResponse(
                action_kind="speak",
                action_payload=payload,
                post_action_route="KEEP_NEXT",
                next_perceptions=next_perceptions,
                session_id=session_id,
                turn_id=turn_id,
                correlation_id=correlation_id,
            )
        payload: dict[str, object] = {}
        self._action_validator.validate("rest", payload)
        return LLMResponse(
            action_kind="rest",
            action_payload=payload,
            post_action_route="END_SESSION",
            next_perceptions=(),
            session_id=session_id,
            turn_id=turn_id,
            correlation_id=correlation_id,
        )

    def _available(self, kinds: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(kind for kind in kinds if self._capability_of(kind))

    def _dedupe_available(
        self,
        kinds: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        return tuple(
            kind
            for kind in kinds
            if kind not in seen
            and not seen.add(kind)
            and self._capability_of(kind)
        )

    async def _abort_resources(self) -> None:
        await self._llm.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._llm.force_abort()
