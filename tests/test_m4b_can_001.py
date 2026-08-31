"""M4B-CAN-001 — typed cancellation and destructive owner report."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path

import pytest
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.cognition.reasoner import Reasoner
from sbd.cognition.litert_lm.adapter import LLMFatalError, SubprocessLLMChild
from sbd.cognition.litert_lm.lock import LLMArtifactLock
from sbd.core.config.models import LLMConfig
from sbd.core.state_manager.convergence import CancelTimeoutPolicy, DefaultSessionConverger
from tests.test_m4b_gen_001 import _adapter, _input
from tests.test_m2_wrk_003 import _bus_records, _validator


def test_m4b_can_001_abort_sends_one_matching_cancel_and_next_turn_succeeds() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        child = children[0]
        original_send = child.send
        generate_calls = 0
        async def send(frame):
            nonlocal generate_calls
            if frame["type"] == "CANCEL":
                child.frames.append(dict(frame))
                await child.terminals.put({
                    "type": "CANCELLED", "protocol_version": "snowboard.llm/1",
                    "request_id": frame["request_id"], "state": "READY",
                })
            else:
                generate_calls += 1
                if generate_calls == 1:
                    child.frames.append(dict(frame))
                else:
                    await original_send(frame)
        child.send = send  # type: ignore[method-assign]

        after_terminal = adapter._after_terminal
        terminal_entered = asyncio.Event()
        permit_cleanup = asyncio.Event()
        async def delayed_after_terminal(owner):
            terminal_entered.set()
            await permit_cleanup.wait()
            await after_terminal(owner)
        adapter._after_terminal = delayed_after_terminal  # type: ignore[method-assign]

        generation = asyncio.create_task(adapter.generate(_input()))
        while not child.frames:
            await asyncio.sleep(0)
        abort1 = asyncio.create_task(adapter.abort())
        abort2 = asyncio.create_task(adapter.abort())
        await terminal_entered.wait()
        abort_after_terminal = asyncio.create_task(adapter.abort())
        await asyncio.sleep(0)
        assert not abort1.done() and not abort2.done() and not abort_after_terminal.done()
        assert adapter.last_cancel_evidence is not None
        permit_cleanup.set()
        results = await asyncio.gather(
            generation, abort1, abort2, abort_after_terminal, return_exceptions=True,
        )
        assert type(results[0]).__name__ == "AdapterTimeout"
        assert [frame["type"] for frame in child.frames].count("CANCEL") == 1
        assert adapter.last_cancel_evidence is not None
        assert adapter.last_cancel_evidence.native_cancel_calls == 1
        assert adapter.last_cancel_evidence.worker_joined is True
        assert adapter.state.name == "READY"
        assert (await adapter.generate(_input())).response["action_kind"] == "rest"
    asyncio.run(scenario())


def test_m4b_can_001_force_abort_reports_stable_destroyed_key() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        report = await adapter.force_abort()
        assert report.destroyed_backends == ("backend.cognition.reasoner.llm",)
        assert children[0].terminated == 1
    asyncio.run(scenario())


def test_m4b_can_001_force_abort_converges_active_terminal_wait() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        child = children[0]

        async def pending_send(frame):
            child.frames.append(dict(frame))

        child.send = pending_send  # type: ignore[method-assign]
        generation = asyncio.create_task(adapter.generate(_input()))
        while not child.frames:
            await asyncio.sleep(0)
        report = await adapter.force_abort()
        terminal = await asyncio.gather(generation, return_exceptions=True)

        assert report.destroyed_backends == ("backend.cognition.reasoner.llm",)
        assert child.terminated == 1
        assert type(terminal[0]).__name__ == "CancelledError"
        assert adapter.state.name == "DESTROYED"
        assert adapter._terminal_task is None

    asyncio.run(scenario())


def test_m4b_can_001_level_two_finishes_reasoner_outer_task_without_level_three() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        child = children[0]

        async def pending_send(frame):
            child.frames.append(dict(frame))

        child.send = pending_send  # type: ignore[method-assign]
        bus, responses, errors = _bus_records()
        reasoner = Reasoner(
            adapter, PromptBuilder(), bus, {"listen", "speak"}.__contains__, _validator(),
        )
        operation = asyncio.create_task(reasoner.reason("s", 1, 1, (), ()))
        while not child.frames:
            await asyncio.sleep(0)
        target = SimpleNamespace(
            correlation_id=1, kind="cognition.reasoner", phase="reasoning",
            worker=reasoner, task=operation,
        )
        converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy(
            abort_by_kind={"cognition.reasoner": 0.01},
            force_abort_by_kind={"cognition.reasoner": 0.5},
        ))

        result = await converger.converge((target,), trigger="error")

        assert result.destroyed_backends == ("backend.cognition.reasoner.llm",)
        assert operation.done() and not operation.cancelled()
        assert child.terminated == 1
        assert responses == [] and errors == []

    asyncio.run(scenario())


def test_m4b_can_001_workdir_residue_is_fatal_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        lock = LLMArtifactLock.load(
            Path(__file__).parent.parent / "requirements/m4b/llm-artifacts.json",
        )
        child = SubprocessLLMChild(LLMConfig(), lock, 1)
        child._workdir = tmp_path / "m4b-residue"
        child._workdir.mkdir()
        monkeypatch.setattr("sbd.cognition.litert_lm.adapter.shutil.rmtree", lambda path: None)
        with pytest.raises(LLMFatalError, match="work-directory cleanup"):
            await child._cleanup()
        assert child._workdir is not None

    asyncio.run(scenario())


def test_m4b_can_001_generation_deadline_sends_cancel_then_uses_terminal_grace() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        adapter._cfg = replace(  # injected clocks; production shape remains locked
            adapter._cfg, generation_timeout_seconds=0.01, terminal_grace_seconds=0.1,
        )
        await adapter.start()
        child = children[0]
        async def send(frame):
            child.frames.append(dict(frame))
            if frame["type"] == "CANCEL":
                await child.terminals.put({
                    "type": "CANCELLED", "protocol_version": "snowboard.llm/1",
                    "request_id": frame["request_id"], "state": "READY",
                })
        child.send = send  # type: ignore[method-assign]
        result = await asyncio.gather(adapter.generate(_input()), return_exceptions=True)
        assert type(result[0]).__name__ == "AdapterTimeout"
        assert [frame["type"] for frame in child.frames] == ["GENERATE", "CANCEL"]
    asyncio.run(scenario())


def test_m4b_can_001_cancel_write_failure_destroys_owner() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        await adapter.start()
        child = children[0]

        async def send(frame):
            child.frames.append(dict(frame))
            if frame["type"] == "CANCEL":
                raise BrokenPipeError("injected private pipe failure")

        child.send = send  # type: ignore[method-assign]
        generation = asyncio.create_task(adapter.generate(_input()))
        while not child.frames:
            await asyncio.sleep(0)
        with pytest.raises(LLMFatalError, match="cancellation write"):
            await adapter.abort()
        terminal = await asyncio.gather(generation, return_exceptions=True)
        assert type(terminal[0]).__name__ == "CancelledError"
        assert child.terminated == 1
        assert adapter.state.name == "DESTROYED"

    asyncio.run(scenario())


def test_m4b_can_001_deadline_cancel_write_failure_destroys_owner() -> None:
    async def scenario() -> None:
        adapter, children, _ = _adapter()
        adapter._cfg = replace(adapter._cfg, generation_timeout_seconds=0.01)
        await adapter.start()
        child = children[0]

        async def send(frame):
            child.frames.append(dict(frame))
            if frame["type"] == "CANCEL":
                raise BrokenPipeError("injected private pipe failure")

        child.send = send  # type: ignore[method-assign]
        with pytest.raises(LLMFatalError, match="cancellation write"):
            await adapter.generate(_input())
        assert child.terminated == 1
        assert adapter.state.name == "DESTROYED"

    asyncio.run(scenario())
