"""M4A-TTS-002 — persistence, error, cancellation, force-abort, and rebuild."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.action.speak.matcha.adapter import MatchaTTSAdapter, TTS_ERROR_CODES, TTS_KEY
from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterRejected, AdapterUnavailable
from sbd.adaptor.framed_child import AudioProtocolError, ChildState
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import TTSConfig
from sbd.core.event_bus import EventBus
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase
from tests.fakes.m4a import ScriptedChild


LOCK = AudioArtifactLock.load(Path(__file__).parent.parent / "requirements/m4a/audio-artifacts.json")
CONFIG = TTSConfig(driver="sherpa_matcha")


def _header(payload: bytes, request_id: int):
    return {"protocol":1,"event":"PCM","request_id":request_id,"sample_rate_hz":16000,"channels":1,"sample_format":"S16_LE","sample_count":len(payload)//2,"payload_bytes":len(payload),"pcm_sha256":hashlib.sha256(payload).hexdigest()}


def _app_config():
    return replace(DEFAULT_CONFIG, action=replace(DEFAULT_CONFIG.action, tts=CONFIG))


class _ReadyResource:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


def _register_required_workers(rm: ResourceManager) -> None:
    for key, capability in (
        ("worker.perception.listen", "listen"),
        ("worker.cognition.reasoner", None),
        ("worker.action.rest", None),
    ):
        rm.register(ResourceSpec(
            key=key,
            phase=StartPhase.WORKER,
            factory=lambda resolver: _ReadyResource(),
            capability_kind=capability,
        ))


def test_m4a_tts_002_persistent_error_reopen_and_next_success() -> None:
    async def run() -> None:
        payload = b"\x01\x00"
        child = ScriptedChild([
            {"protocol":1,"event":"ERROR","request_id":1,"code":"GENERATION_REJECTED"},
            _header(payload, 2),
        ], payload=payload)
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start(); await adapter.start()
        with pytest.raises(AdapterRejected, match="GENERATION_REJECTED"):
            [chunk async for chunk in adapter.synthesize("first")]
        assert [chunk async for chunk in adapter.synthesize("second")] == [payload]
        assert child.start_count == 1 and child.request_id == 2

    asyncio.run(run())


@pytest.mark.parametrize("code", sorted(TTS_ERROR_CODES))
def test_m4a_tts_002_every_whitelisted_error_reopens_same_child(code: str) -> None:
    async def run() -> None:
        payload = b"\x01\x00"
        child = ScriptedChild([
            {"protocol": 1, "event": "ERROR", "request_id": 1, "code": code},
            _header(payload, 2),
        ], payload=payload)
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(AdapterRejected, match=code):
            [chunk async for chunk in adapter.synthesize("first")]
        assert [chunk async for chunk in adapter.synthesize("second")] == [payload]
        assert child.start_count == 1 and child.state is ChildState.READY

    asyncio.run(run())


def test_m4a_tts_002_unknown_error_eof_and_late_terminal_are_protocol_failures() -> None:
    async def unknown() -> None:
        child = ScriptedChild([{
            "protocol": 1, "event": "ERROR", "request_id": 1, "code": "UNKNOWN",
        }])
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(AudioProtocolError, match="unknown"):
            [chunk async for chunk in adapter.synthesize("private")]
        assert child.state is ChildState.DESTROYED

    async def eof() -> None:
        child = ScriptedChild()
        child.receive_release.set()
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(EOFError):
            [chunk async for chunk in adapter.synthesize("private")]
        assert child.state is ChildState.DESTROYED

    async def late() -> None:
        payload = b"\x01\x00"
        child = ScriptedChild([
            _header(payload, 1),
            {"protocol": 1, "event": "CANCELLED", "request_id": 1},
        ], payload=payload)
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        assert [chunk async for chunk in adapter.synthesize("first")] == [payload]
        with pytest.raises(AudioProtocolError):
            [chunk async for chunk in adapter.synthesize("second")]
        assert child.state is ChildState.DESTROYED

    asyncio.run(unknown())
    asyncio.run(eof())
    asyncio.run(late())


def test_m4a_tts_002_single_flight_rejects_without_queueing() -> None:
    async def run() -> None:
        child = ScriptedChild()
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        first = adapter.synthesize("first")
        task = asyncio.create_task(anext(first))
        await child.receive_entered.wait()
        second = adapter.synthesize("second")
        with pytest.raises(AdapterUnavailable, match="busy"):
            await anext(second)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        report = await adapter.force_abort()
        assert report.destroyed_backends == (TTS_KEY,)

    asyncio.run(run())


def test_m4a_tts_002_cooperative_cancel_returns_same_child_to_ready() -> None:
    async def run() -> None:
        payload = b"\x01\x00"
        child = ScriptedChild(
            payload=payload,
            cancel_events=[{
                "protocol": 1, "event": "CANCELLED", "request_id": 1,
            }],
        )
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        operation = asyncio.create_task(anext(adapter.synthesize("first")))
        await child.receive_entered.wait()
        await adapter.abort()
        with pytest.raises(AdapterRejected, match="cancelled"):
            await operation
        assert child.state is ChildState.READY
        assert child.max_active_receivers == 1
        child.events.append(_header(payload, 2))
        assert [chunk async for chunk in adapter.synthesize("second")] == [payload]
        assert child.start_count == 1

    asyncio.run(run())


def test_m4a_tts_002_deferred_cancel_force_abort_stable_key_and_rebuild() -> None:
    async def run() -> None:
        original = ScriptedChild(cancel_events=[{
            "protocol": 1, "event": "CANCEL_DEFERRED", "request_id": 1,
        }])
        replacement = ScriptedChild()
        children = iter((original, replacement))
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: next(children))
        await adapter.start()
        operation = asyncio.create_task(anext(adapter.synthesize("private")))
        await original.receive_entered.wait()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(adapter.abort(), 0.01)
        assert original.max_active_receivers == 1
        report = await adapter.force_abort()
        assert report.destroyed_backends == (TTS_KEY,)
        assert original.force_count == 1 and adapter.state is ChildState.DESTROYED
        operation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        await adapter.rebuild(None, _app_config())
        assert adapter.state is ChildState.READY and replacement.start_count == 1

    asyncio.run(run())


def test_m4a_tts_002_resource_manager_barrier_reopens_after_same_owner_ready() -> None:
    async def run() -> None:
        payload = b"\x01\x00"
        original = ScriptedChild()
        replacement = ScriptedChild([_header(payload, 1)], payload=payload)
        children = iter((original, replacement))
        adapter = MatchaTTSAdapter(
            CONFIG, lock=LOCK, child_factory=lambda: next(children),
        )
        config = _app_config()
        rm = ResourceManager(config, EventBus())
        rm.register(ResourceSpec(
            key=TTS_KEY,
            phase=StartPhase.BACKEND,
            factory=lambda resolver: adapter,
            recoverable=True,
            recovery_hook=adapter,
        ))
        _register_required_workers(rm)
        await rm.start()
        assert adapter.state is ChildState.READY

        await adapter.force_abort()
        ticket = rm.begin_recovery((TTS_KEY,))
        assert rm.recovery_ready() is False
        await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is True
        assert adapter.state is ChildState.READY
        assert replacement.start_count == 1
        assert [chunk async for chunk in adapter.synthesize("recovered")] == [payload]
        await rm.stop_all()

    asyncio.run(run())
