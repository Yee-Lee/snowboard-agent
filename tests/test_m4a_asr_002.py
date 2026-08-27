"""M4A-ASR-002 — persistent child and request-local multi-turn behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterRejected
from sbd.adaptor.framed_child import AudioProtocolError, ChildState
from sbd.core.config.models import ASRConfig
from sbd.perception.listen.whispercpp.adapter import ASR_ERROR_CODES, WhisperCppASRAdapter
from tests.fakes.m4a import ScriptedChild, asr_endpoint, asr_result


LOCK = AudioArtifactLock.load(Path(__file__).parent.parent / "requirements/m4a/audio-artifacts.json")
CONFIG = ASRConfig(driver="whispercpp")


async def _one_frame():
    yield b"\x00" * 640


def test_m4a_asr_002_persistent_success_empty_and_error_reopen() -> None:
    async def run() -> None:
        child = ScriptedChild([
            asr_endpoint(1, 1), asr_result(1, "first"),
            asr_endpoint(2, 1), asr_result(2, ""),
            asr_endpoint(3, 1), {"protocol": 1, "event": "ERROR", "request_id": 3, "code": "NO_SPEECH"},
            asr_endpoint(4, 1), asr_result(4, "fresh"),
        ])
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        await adapter.start()
        assert (await adapter.transcribe(_one_frame())).text == "first"
        assert (await adapter.transcribe(_one_frame())).text == ""
        with pytest.raises(AdapterRejected, match="NO_SPEECH"):
            await adapter.transcribe(_one_frame())
        assert (await adapter.transcribe(_one_frame())).text == "fresh"
        assert child.start_count == 1 and child.request_id == 4

    asyncio.run(run())


@pytest.mark.parametrize("code", sorted(ASR_ERROR_CODES))
def test_m4a_asr_002_every_whitelisted_error_reopens_same_child(code: str) -> None:
    async def run() -> None:
        child = ScriptedChild([
            asr_endpoint(1, 1),
            {"protocol": 1, "event": "ERROR", "request_id": 1, "code": code},
            asr_endpoint(2, 1), asr_result(2, "fresh"),
        ])
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(AdapterRejected, match=code):
            await adapter.transcribe(_one_frame())
        assert (await adapter.transcribe(_one_frame())).text == "fresh"
        assert child.start_count == 1 and child.state is ChildState.READY

    asyncio.run(run())


def test_m4a_asr_002_unknown_error_eof_and_late_terminal_are_protocol_failures() -> None:
    async def unknown() -> None:
        child = ScriptedChild([
            asr_endpoint(1, 1),
            {"protocol": 1, "event": "ERROR", "request_id": 1, "code": "UNKNOWN"},
        ])
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(AudioProtocolError, match="unknown"):
            await adapter.transcribe(_one_frame())
        assert child.state is ChildState.DESTROYED

    async def eof() -> None:
        child = ScriptedChild()
        child.receive_release.set()
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(EOFError):
            await adapter.transcribe(_one_frame())
        assert child.state is ChildState.DESTROYED

    async def late() -> None:
        child = ScriptedChild([
            asr_endpoint(1, 1), asr_result(1, "first"),
            asr_result(1, "late"),
        ])
        adapter = WhisperCppASRAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        assert (await adapter.transcribe(_one_frame())).text == "first"
        with pytest.raises(AudioProtocolError):
            await adapter.transcribe(_one_frame())
        assert child.state is ChildState.DESTROYED

    asyncio.run(unknown())
    asyncio.run(eof())
    asyncio.run(late())
