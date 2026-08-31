"""M4B-RDY-001 — deterministic parent admission and request identity seam."""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.cognition.litert_lm.adapter import LLMFatalError, _load_startup_evidence
from sbd.cognition.litert_lm.lock import LLMLockError
from sbd.cognition.litert_lm.worker import (
    LiteRTRuntime, WorkerCancelFailed, _terminal_from_outcome,
    _write_startup_evidence,
)
from sbd.cognition.llm_child_protocol import (
    LLMProtocolError,
    LLMReadyIdentity,
    LLMWireCancelled,
    PROTOCOL_VERSION,
)
from sbd.cognition.prompt_builder import ReasoningInput, ReasoningPerception
from tests.fakes.m4b_llm_child import ScriptedLLMChild
from tests.test_m4b_gen_001 import _adapter


def _identity() -> LLMReadyIdentity:
    return LLMReadyIdentity(
        candidate_id="CAND-LRT-G4E2B-MOBILE-R1",
        pairing_revision="litert-lm-v0.16.0-pi-g2b-r5",
        platform="pi-debian13-aarch64",
        runtime_sha256="a" * 64,
        model_sha256="b" * 64,
        config_sha256="c" * 64,
    )


def _input() -> ReasoningInput:
    return ReasoningInput(
        perceptions=(ReasoningPerception("listen", "ok", "private request"),),
        pending_message_count=0,
        available_perceptions=("listen",),
        available_actions=("speak", "rest"),
        tool_schemas=(),
    )


def test_m4b_rdy_001_cancel_intent_discards_raced_result_as_typed_cancelled() -> None:
    private_response = {
        "action_kind": "speak",
        "action_payload": {"text": "PRIVATE_RACED_RESULT"},
        "next_perceptions": ["listen"],
    }
    terminal = _terminal_from_outcome(
        "llm.1.1", "result", (private_response, {"decode_tokens": 1}),
        cancel_sent=True,
    )
    assert terminal == {
        "type": "CANCELLED", "protocol_version": PROTOCOL_VERSION,
        "request_id": "llm.1.1", "state": "READY",
    }
    assert "PRIVATE_RACED_RESULT" not in json.dumps(terminal)
    for kind in ("cancelled", "invalid_request", "error"):
        assert _terminal_from_outcome(
            "llm.1.1", kind, None, cancel_sent=True,
        ) == terminal


def test_m4b_rdy_001_cancel_before_conversation_binding_calls_native_once() -> None:
    class Conversation:
        cancel_calls = 0

        def cancel_process(self) -> None:
            self.cancel_calls += 1

    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._active = None
    runtime._pending_cancel = False
    runtime._cancel_requested = False
    runtime._lock = threading.Lock()
    conversation = Conversation()

    runtime.cancel()
    assert runtime._pending_cancel is True and conversation.cancel_calls == 0
    assert runtime._activate(conversation) is True
    assert runtime._pending_cancel is False and conversation.cancel_calls == 1
    runtime._deactivate()


def test_m4b_rdy_001_deferred_native_cancel_failure_is_fatal_typed_error() -> None:
    class Conversation:
        def cancel_process(self) -> None:
            raise RuntimeError("private native failure")

    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._active = None
    runtime._pending_cancel = False
    runtime._cancel_requested = False
    runtime._lock = threading.Lock()
    runtime.cancel()
    with pytest.raises(WorkerCancelFailed, match="native cancellation failed"):
        runtime._activate(Conversation())
    assert _terminal_from_outcome(
        "llm.1.1", "cancel_failed", None, cancel_sent=True,
    ) == {
        "type": "ERROR", "protocol_version": PROTOCOL_VERSION,
        "request_id": "llm.1.1", "code": "CANCEL_FAILED", "state": "FATAL",
    }


@pytest.mark.parametrize("failed_stage", ["runtime", "config"])
def test_m4b_rdy_001_authenticates_installed_product_before_child_factory(
    tmp_path: Path, failed_stage: str,
) -> None:
    class Closure:
        def verify_install(self, root: Path) -> None:
            if failed_stage == "runtime":
                raise LLMLockError("injected runtime drift")

    class Lock:
        runtime_closure = Closure()

        def verify_config_paths(self, cfg) -> None:
            if failed_stage == "config":
                raise LLMLockError("injected config drift")

    async def scenario() -> None:
        adapter, children, _ = _adapter()
        adapter._lock = Lock()  # type: ignore[assignment]
        adapter._cfg = replace(
            adapter._cfg,
            runtime_python=tmp_path / "runtime/bin/python",
        )
        with pytest.raises(LLMFatalError, match="product authentication"):
            await adapter.start()
        assert children == []
        assert adapter.state.name == "STOPPED"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "state",
    ["AUTHENTICATING", "STARTING", "ENGINE_LOADED", "PREWARMING"],
)
def test_m4b_rdy_001_non_ready_parent_admission_is_local_and_zero_write(
    state: str,
) -> None:
    child = ScriptedLLMChild(_identity())
    child.set_state(state)
    with pytest.raises(LLMProtocolError, match="requires READY"):
        child.admit(_input())
    assert child.frames == []
    assert child.inference_calls == 0
    assert child.active is None


def test_m4b_rdy_001_single_flight_never_writes_second_generate() -> None:
    child = ScriptedLLMChild(_identity(), child_generation=7)
    child.set_state("READY")
    request_id = child.admit(_input())
    active = child.active
    assert request_id == "llm.7.1"
    with pytest.raises(LLMProtocolError, match="requires READY"):
        child.admit(_input())
    assert len(child.frames) == 1
    assert child.inference_calls == 1
    assert child.active == active

    terminal = child.complete({
        "type": "CANCELLED",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "state": "READY",
    })
    assert isinstance(terminal, LLMWireCancelled)
    assert len(child.terminals) == 1
    assert child.state == "READY"
    assert child.admit(_input()) == "llm.7.2"


def test_m4b_rdy_001_cancel_is_typed_single_write_for_active_identity() -> None:
    child = ScriptedLLMChild(_identity())
    child.set_state("READY")
    request_id = child.admit(_input())
    cancel = child.cancel()
    assert cancel == {
        "type": "CANCEL",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
    }
    assert child.native_cancel_calls == 1
    assert [frame["type"] for frame in child.frames] == ["GENERATE", "CANCEL"]


def test_m4b_rdy_001_startup_evidence_is_sanitized_and_exact(tmp_path: Path) -> None:
    path = tmp_path / "startup-evidence.json"
    _write_startup_evidence(path, engine_load_latency_ms=12.5, prewarm_latency_ms=3.25)
    evidence = _load_startup_evidence(path, ready_latency_ms=18.0)
    assert evidence.engine_load_latency_ms == 12.5
    assert evidence.prewarm_latency_ms == 3.25
    assert evidence.ready_latency_ms == 18.0
    assert evidence.prewarm_prompt_sha256 == "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d"
    assert set(json.loads(path.read_text())) == {
        "schema_version", "engine_load_latency_ms", "prewarm_latency_ms",
        "prewarm_prompt_sha256",
    }


def test_m4b_rdy_001_startup_evidence_rejects_extra_or_wrong_prompt(tmp_path: Path) -> None:
    for value in (
        {
            "schema_version": 1, "engine_load_latency_ms": 1.0,
            "prewarm_latency_ms": 1.0, "prewarm_prompt_sha256": "0" * 64,
        },
        {
            "schema_version": 1, "engine_load_latency_ms": 1.0,
            "prewarm_latency_ms": 1.0,
            "prewarm_prompt_sha256": "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d",
            "private_path": "/tmp/private",
        },
    ):
        path = tmp_path / "startup-evidence.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(LLMFatalError, match="startup evidence"):
            _load_startup_evidence(path, ready_latency_ms=2.0)
