"""Regression for interrupted provisional speech and repeated native TTS stop."""
import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.action.speak import Speak
from sbd.action.speak.matcha.adapter import MatchaTTSAdapter
from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.framed_child import AudioProtocolError, ChildState, FramedProcess
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.config.models import TTSConfig
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.lifecycle import ForceAbortReport
from tests.fakes.m4a import ScriptedChild
from tests.test_m2_wrk_003 import _bus_records, _validator
from tests.test_m4b_outcome_001 import ProductLLM, fact
from tests.test_m4a_tts_001 import _header

LOCK = AudioArtifactLock.load(Path(__file__).resolve().parents[1] / "requirements/m4a/audio-artifacts.json")


@pytest.mark.parametrize("mode", ["graceful", "forced"])
def test_interrupted_reasoner_releases_streaming_claim_and_next_conversation_works(mode):
    async def scenario():
        cancelled = {"protocol": 1, "event": "CANCELLED", "request_id": 1}
        child = ScriptedChild(cancel_events=[cancelled] if mode == "graceful" else [])
        replacement = ScriptedChild()
        children = iter([child, replacement])
        cfg = TTSConfig(driver="sherpa_matcha")
        tts = MatchaTTSAdapter(cfg, lock=LOCK, child_factory=lambda: next(children))
        await tts.start()
        bus, responses, errors = _bus_records()
        speaker = Speak(tts=tts, audio_output=MockAudioOutput(), bus=bus)

        class StreamingLLM(ProductLLM):
            supports_safe_text_callback = True
            claim = ("session", 1)

            def assert_conversation(self, sid, generation):
                assert self.owner is asyncio.current_task()
                assert (sid, generation) == self.claim

            async def generate(self, snapshot, text, *, on_safe_text):
                await on_safe_text(0, "好")
                self.generate_entered.set()
                await self.release.wait()
                if self.aborted:
                    raise asyncio.CancelledError
                return self.result

            async def force_abort(self):
                await self.abort()
                return ForceAbortReport(("backend.cognition.reasoner.llm",))

        llm = StreamingLLM(blocked=True)
        reasoner = Reasoner(llm, ListenProjector(), bus, {"listen", "speak"}.__contains__,
                            _validator(), streaming_speak=speaker)
        task = asyncio.create_task(reasoner.reason("session", 1, 1, (fact(),), (),
                                                   conversation_generation=1))
        try:
            await asyncio.wait_for(child.receive_entered.wait(), 1)
            assert child.state is ChildState.BUSY
            if mode == "forced":
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(reasoner.abort(), 0.05)
                report = await asyncio.wait_for(reasoner.force_abort(), 1)
                assert report.destroyed_backends == (
                    "backend.action.speak.tts", "backend.cognition.reasoner.llm")
                assert child.state is ChildState.DESTROYED
                config = replace(DEFAULT_CONFIG, action=replace(DEFAULT_CONFIG.action, tts=cfg))
                await tts.rebuild(bus, config)
                next_child = replacement
                request_id = 1
            else:
                await asyncio.wait_for(reasoner.abort(), 1)
                assert child.state is ChildState.READY
                assert child.force_count == 0
                next_child = child
                request_id = 2
            await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), 1)
            assert speaker._streaming is None
            assert reasoner._active is None
            assert responses == [] and errors == []
            assert child.active_receivers == 0

            payload = b"\x01\x00" * 320
            next_child.events.append(_header(payload, request_id))
            next_child.payload = payload
            llm.aborted = False
            llm.claim = ("next-session", 2)
            await asyncio.wait_for(reasoner.reason("next-session", 1, 2,
                (fact(session_id="next-session"),), (), conversation_generation=2), 1)
            assert len(responses) == 1 and errors == []
            await asyncio.wait_for(speaker.execute("next-session", 1, 2, {"text": "好"}), 1)
            assert speaker._streaming is None
            assert next_child.state is ChildState.READY
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await tts.force_abort()

    asyncio.run(scenario())


def test_double_stop_of_destroyed_tts_is_safe(tmp_path):
    async def scenario():
        child = FramedProcess(argv_builder=lambda directory: [], work_root=tmp_path,
                              expected_ready={}, ready_timeout=1,
                              terminate_timeout=1, kill_timeout=1, environment={})
        adapter = MatchaTTSAdapter(TTSConfig(driver="sherpa_matcha"), lock=LOCK,
                                  child_factory=lambda: child)
        child.state = ChildState.BUSY
        await adapter.stop()  # Forced stop has no process here, but real state transition.
        assert child.state is ChildState.DESTROYED
        await adapter.stop()
        assert child.state is ChildState.DESTROYED

    asyncio.run(scenario())
