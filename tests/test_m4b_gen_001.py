"""M4B-GEN-001 — persistent parent, single-flight and fresh request identity."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from sbd.adaptor.errors import AdapterRejected
from sbd.cognition.litert_lm.adapter import (
    AdapterState, LLMFatalError, LiteRTLMAdapter,
)
from sbd.cognition.litert_lm.lock import LLMArtifactLock
from sbd.cognition.litert_lm.worker import LiteRTRuntime, WorkerInputTooLarge
from sbd.cognition.llm import LLMResourceSample
from sbd.cognition.llm_child_protocol import PROTOCOL_VERSION
from sbd.cognition.prompt_builder import ReasoningInput
from sbd.core.config.models import LLMConfig
from sbd.core.resource_manager.models import RecoveryTicket


ROOT = Path(__file__).parent.parent


def _input() -> ReasoningInput:
    return ReasoningInput((), 0, (), ("rest",), ())


def _result(request_id: str) -> dict[str, object]:
    return {
        "type": "RESULT", "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "response": {"action_kind": "rest", "action_payload": {}, "next_perceptions": []},
        "metrics": {
            "init_ms": 0.0, "ttft_ms": 1.0, "prefill_tokens": 1,
            "prefill_tokens_per_second": 1.0, "decode_tokens": 1,
            "decode_tokens_per_second": 1.0, "kv_tokens": 1,
        },
        "state": "READY",
    }


class Child:
    def __init__(self, lock: LLMArtifactLock, generation: int) -> None:
        self.pid = 100 + generation
        self.pgid = self.pid
        self.lock = lock
        self.frames: list[dict[str, object]] = []
        self.terminals: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self.stopped = 0
        self.terminated = 0

    async def start(self):
        identity = self.lock.identity
        return {"type": "READY", "protocol_version": PROTOCOL_VERSION, "state": "READY", "identity": {
            "candidate_id": identity.candidate_id, "pairing_revision": identity.pairing_revision,
            "platform": identity.platform, "runtime_sha256": identity.runtime_sha256,
            "model_sha256": identity.model_sha256, "config_sha256": identity.config_sha256,
        }}

    async def send(self, frame):
        self.frames.append(dict(frame))
        if frame["type"] == "GENERATE":
            await self.terminals.put(_result(frame["request_id"]))

    async def receive(self): return await self.terminals.get()
    async def stop(self): self.stopped += 1
    async def force_terminate(self): self.terminated += 1


class Sampler:
    def __init__(self) -> None: self.calls = 0
    def sample(self, *, child_pid: int, child_pgid: int):
        self.calls += 1
        return LLMResourceSample(100, 2 * 1024**3)


def _adapter(*, recycle: int = 8):
    lock = LLMArtifactLock.load(ROOT / "requirements/m4b/llm-artifacts.json")
    children: list[Child] = []
    tickets: list[RecoveryTicket] = []
    def factory(cfg, product, generation):
        child = Child(product, generation)
        children.append(child)
        return child
    def schedule(keys):
        ticket = RecoveryTicket(len(tickets) + 1, keys)  # type: ignore[arg-type]
        tickets.append(ticket)
        return ticket
    async def wait(ticket): return None
    cfg = LLMConfig(recycle_max_inference_attempts=recycle)
    adapter = LiteRTLMAdapter(
        cfg, lock=lock, schedule_recovery=schedule, wait_recovery=wait,
        resource_sampler=Sampler(), child_factory=factory,
    )
    return adapter, children, tickets


def test_m4b_gen_001_persistent_child_and_monotonic_requests() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        assert adapter.state_trace == [
            AdapterState.STOPPED, AdapterState.AUTHENTICATING,
            AdapterState.STARTING, AdapterState.ENGINE_LOADED,
            AdapterState.PREWARMING, AdapterState.READY,
        ]
        await adapter.generate(_input())
        await adapter.generate(_input())
        assert len(children) == 1
        assert [frame["request_id"] for frame in children[0].frames] == ["llm.1.1", "llm.1.2"]
        assert adapter.state is AdapterState.READY
    asyncio.run(scenario())


def test_m4b_gen_001_startup_identity_failure_cleans_and_same_owner_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Child.start
    calls = 0
    async def first_bad(self):
        nonlocal calls
        calls += 1
        frame = await original(self)
        if calls == 1:
            frame["identity"]["candidate_id"] = "wrong"
        return frame
    monkeypatch.setattr(Child, "start", first_bad)

    async def scenario() -> None:
        adapter, children, _ = _adapter()
        with pytest.raises(LLMFatalError, match="startup"):
            await adapter.start()
        assert children[0].terminated == 1 and adapter.state is AdapterState.STOPPED
        await adapter.start()
        assert len(children) == 2 and adapter.state is AdapterState.READY
    asyncio.run(scenario())


def test_m4b_gen_001_initial_sample_failure_cleans_before_ready() -> None:
    class InvalidSampler:
        def sample(self, **kwargs): return LLMResourceSample(True, 1)  # type: ignore[arg-type]

    async def scenario() -> None:
        adapter, children, _ = _adapter()
        adapter._sampler = InvalidSampler()
        with pytest.raises(LLMFatalError, match="startup"):
            await adapter.start()
        assert children[0].terminated == 1
        assert adapter.state is AdapterState.STOPPED
        assert AdapterState.READY not in adapter.state_trace
    asyncio.run(scenario())


def test_m4b_gen_001_concurrent_generation_returns_busy_without_harming_first() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        original = children[0].send
        entered = asyncio.Event()
        release = asyncio.Event()
        async def blocked(frame):
            entered.set()
            await release.wait()
            await original(frame)
        children[0].send = blocked  # type: ignore[method-assign]
        first = asyncio.create_task(adapter.generate(_input()))
        await entered.wait()
        with pytest.raises(AdapterRejected, match="BUSY"):
            await adapter.generate(_input())
        release.set()
        await first
        assert adapter.state is AdapterState.READY
        assert len(children[0].frames) == 1
        await adapter.generate(_input())
    asyncio.run(scenario())


def test_m4b_gen_001_eighth_attempt_schedules_same_owner_recycle() -> None:
    async def scenario() -> None:
        adapter, children, tickets = _adapter()
        await adapter.start()
        for _ in range(8):
            await adapter.generate(_input())
        assert len(tickets) == 1
        assert tickets[0].keys == ("backend.cognition.reasoner.llm",)
        assert adapter.state is AdapterState.RECYCLE_PENDING
        await adapter.rebuild()
        assert children[0].stopped == 1 and len(children) == 2
        assert adapter.state is AdapterState.READY
        await adapter.generate(_input())
        assert children[1].frames[0]["request_id"] == "llm.2.1"
    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("delta", "mem_available", "triggered"),
    [
        (48 * 1024**2 - 1, 768 * 1024**2, False),
        (48 * 1024**2, 768 * 1024**2, True),
        (0, 768 * 1024**2 - 1, True),
    ],
)
def test_m4b_gen_001_recycle_uses_exact_raw_byte_thresholds(
    delta: int, mem_available: int, triggered: bool,
) -> None:
    class SequenceSampler:
        def __init__(self): self.calls = 0
        def sample(self, **kwargs):
            self.calls += 1
            return (
                LLMResourceSample(100, 2 * 1024**3)
                if self.calls == 1
                else LLMResourceSample(100 + delta, mem_available)
            )

    async def scenario() -> None:
        adapter, _, tickets = _adapter()
        adapter._sampler = SequenceSampler()
        await adapter.start()
        await adapter.generate(_input())
        assert bool(tickets) is triggered
        assert (adapter.state is AdapterState.RECYCLE_PENDING) is triggered
    asyncio.run(scenario())


@pytest.mark.parametrize(("token_count", "accepted"), [(128, True), (129, False)])
def test_m4b_gen_001_uses_rendered_chat_template_token_boundary_before_inference(
    token_count: int, accepted: bool,
) -> None:
    class Info:
        init_time_in_second = 0.0
        time_to_first_token_in_second = 0.001
        last_prefill_token_count = 128
        last_prefill_tokens_per_second = 1.0
        last_decode_token_count = 1
        last_decode_tokens_per_second = 1.0

    class Conversation:
        token_count = 129
        sent = 0
        closed = 0

        def render_message_to_string(self, prompt):
            assert prompt.startswith("Return exactly one JSON object")
            return "rendered-with-model-chat-template"

        def send_message(self, *args, **kwargs):
            self.sent += 1
            return {"action_kind": "rest", "action_payload": {}, "next_perceptions": []}

        def get_benchmark_info(self):
            return Info()

        def close(self):
            self.closed += 1

    conversation = Conversation()

    class Engine:
        def create_conversation(self, **kwargs):
            return conversation

        def tokenize(self, rendered):
            assert rendered == "rendered-with-model-chat-template"
            return list(range(token_count))

    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._engine = Engine()
    runtime._response_format = type(
        "Format", (), {"json": staticmethod(lambda schema: schema)},
    )
    runtime._constraint = object()
    runtime._cancelled_error = type("Cancelled", (RuntimeError,), {})
    runtime._active = None
    runtime._pending_cancel = False
    runtime._cancel_requested = False
    runtime._lock = threading.Lock()
    value = {
        "perceptions": [], "pending_message_count": 0,
        "capabilities": {"perceptions": [], "actions": ["rest"], "tools": []},
    }
    if accepted:
        response, _ = runtime.generate(value)
        assert response["action_kind"] == "rest" and conversation.sent == 1
    else:
        with pytest.raises(WorkerInputTooLarge, match="token limit"):
            runtime.generate(value)
        assert conversation.sent == 0
    assert conversation.closed == 1 and runtime._active is None
