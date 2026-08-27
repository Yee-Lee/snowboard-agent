"""M4A-ASR-003 — abort, force-abort, termination proof, and rebuild."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterRejected, AdapterUnavailable
from sbd.adaptor.framed_child import AudioProtocolError, ChildState
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import ASRConfig
from sbd.core.event_bus import EventBus
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase
from sbd.perception.listen.whispercpp.adapter import ASR_KEY, WhisperCppASRAdapter
from tests.fakes.m4a import ScriptedChild, asr_endpoint, asr_result


LOCK = AudioArtifactLock.load(Path(__file__).parent.parent / "requirements/m4a/audio-artifacts.json")
CONFIG = ASRConfig(driver="whispercpp")


async def _frames():
    yield b"\x00" * 640


class _ReadyResource:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


def _register_required_workers(rm: ResourceManager, dependency: str) -> None:
    rm.register(ResourceSpec(
        key="worker.perception.listen",
        phase=StartPhase.WORKER,
        dependencies=(dependency,),
        factory=lambda resolver: _ReadyResource(),
        capability_kind="listen",
    ))
    for key in ("worker.cognition.reasoner", "worker.action.rest"):
        rm.register(ResourceSpec(
            key=key,
            phase=StartPhase.WORKER,
            factory=lambda resolver: _ReadyResource(),
        ))


def _app_config():
    return replace(DEFAULT_CONFIG, perception=replace(DEFAULT_CONFIG.perception, listen=replace(DEFAULT_CONFIG.perception.listen, adapter=CONFIG)))


def test_m4a_asr_003_cancelled_request_returns_same_child_to_ready() -> None:
    async def run() -> None:
        child = ScriptedChild(cancel_events=[{
            "protocol": 1, "event": "CANCELLED", "request_id": 1,
        }])
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        task = asyncio.create_task(adapter.transcribe(_frames()))
        await child.receive_entered.wait()
        await adapter.abort()
        with pytest.raises(AdapterRejected, match="cancelled"):
            await task
        assert child.state is ChildState.READY
        assert child.max_active_receivers == 1
        assert child.messages[-1][0] == {"protocol": 1, "op": "CANCEL", "request_id": 1}

    asyncio.run(run())


def test_m4a_asr_003_single_flight_rejects_without_queueing() -> None:
    async def run() -> None:
        child = ScriptedChild()
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        first = asyncio.create_task(adapter.transcribe(_frames()))
        await child.receive_entered.wait()
        with pytest.raises(AdapterUnavailable, match="busy"):
            await adapter.transcribe(_frames())
        assert child.request_id == 1
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        await adapter.force_abort()

    asyncio.run(run())


def test_m4a_asr_003_deferred_cancel_force_abort_reports_stable_key_and_rebuilds() -> None:
    async def run() -> None:
        original = ScriptedChild(cancel_events=[{
            "protocol": 1, "event": "CANCEL_DEFERRED", "request_id": 1,
        }])
        replacement = ScriptedChild()
        children = iter((original, replacement))
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: next(children))
        await adapter.start()
        operation = asyncio.create_task(adapter.transcribe(_frames()))
        await original.receive_entered.wait()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(adapter.abort(), 0.01)
        assert original.max_active_receivers == 1
        report = await adapter.force_abort()
        assert report.destroyed_backends == (ASR_KEY,)
        assert original.force_count == 1 and adapter.state is ChildState.DESTROYED
        operation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        await adapter.rebuild(None, _app_config())
        assert adapter.state is ChildState.READY and replacement.start_count == 1

    asyncio.run(run())


def test_m4a_asr_003_wrong_terminal_identity_is_protocol_failure_not_empty_result() -> None:
    async def run() -> None:
        child = ScriptedChild([asr_result(2)])
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(AudioProtocolError):
            await adapter.transcribe(_frames())
        assert child.force_count == 1 and child.state is ChildState.DESTROYED

    asyncio.run(run())


def test_m4a_asr_003_resource_manager_barrier_reopens_after_same_owner_ready() -> None:
    async def run() -> None:
        original = ScriptedChild()
        replacement = ScriptedChild([
            asr_endpoint(1, 1), asr_result(1, "recovered"),
        ])
        children = iter((original, replacement))
        adapter = WhisperCppASRAdapter(
            CONFIG, lock=LOCK, child_factory=lambda: next(children),
        )
        config = _app_config()
        rm = ResourceManager(config, EventBus())
        rm.register(ResourceSpec(
            key=ASR_KEY,
            phase=StartPhase.BACKEND,
            factory=lambda resolver: adapter,
            recoverable=True,
            recovery_hook=adapter,
        ))
        _register_required_workers(rm, ASR_KEY)
        await rm.start()
        assert adapter.state is ChildState.READY

        await adapter.force_abort()
        ticket = rm.begin_recovery((ASR_KEY,))
        assert rm.recovery_ready() is False
        await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is True
        assert adapter.state is ChildState.READY
        assert replacement.start_count == 1
        assert (await adapter.transcribe(_frames())).text == "recovered"
        await rm.stop_all()

    asyncio.run(run())
