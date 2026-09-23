"""M4C-NOINPUT-001 — Session streak and sanitized ASR request codes."""
from __future__ import annotations

import asyncio

import pytest

from sbd.adaptor.errors import AdapterRejected
from sbd.core.event_bus import EventBus
from sbd.core.events import PerceptionResult
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager.manager import StateManager
from sbd.core.state_manager.session import SessionContext
from sbd.perception.listen.listener import Listen


class ProductReasoner:
    _product = True


class Worker:
    async def abort(self): pass
    async def force_abort(self): raise AssertionError


def _manager() -> StateManager:
    catalog = WorkerCatalog()
    catalog.register_perception("listen", Worker())
    catalog.set_reasoner(ProductReasoner())
    catalog.register_action("speak", Worker())
    catalog.register_action("rest", Worker())
    catalog.seal()
    return StateManager(bus=EventBus(), workers=catalog)


def _set_fact(sm: StateManager, fact: PerceptionResult, streak: int = 0) -> None:
    sm._session = SessionContext("session", "button", turn_id=1)
    sm._session.selected_perceptions = ("listen",)
    sm._session.no_input_streak = streak
    sm._session.perception_results = [fact]


@pytest.mark.parametrize(
    ("case", "fact"),
    [
        ("N01", PerceptionResult("listen", "timeout", None)),
        ("N03", PerceptionResult("listen", "error", None, {"asr_error_code": "NO_SPEECH"})),
        ("N04", PerceptionResult("listen", "ok", "   ")),
    ],
)
def test_m4c_noinput_001_first_no_input_retries_same_session(case, fact) -> None:
    sm = _manager()
    _set_fact(sm, fact)
    response = sm._m4c_no_input_response()
    assert response is not None
    assert response.action_payload == {"text": "我沒聽清楚，請再說一次。"}
    assert response.post_action_route == "KEEP_NEXT"
    assert response.next_perceptions == ("listen",)
    assert sm._session is not None and sm._session.no_input_streak == 1


def test_m4c_noinput_001_n02_second_no_input_ends_without_speech() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "timeout", None), streak=1)
    response = sm._m4c_no_input_response()
    assert response is not None
    assert response.action_kind == "rest"
    assert response.action_payload == {}
    assert response.post_action_route == "END_SESSION"
    assert sm._session is not None and sm._session.no_input_streak == 2


def test_m4c_noinput_001_n05_valid_text_resets_before_llm() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "ok", "有效內容"), streak=1)
    assert sm._m4c_no_input_response() is None
    assert sm._session is not None and sm._session.no_input_streak == 0


def test_m4c_noinput_001_n06_new_session_does_not_inherit_streak() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "timeout", None), streak=1)
    sm._session = SessionContext("new-session", "button")
    assert sm._session.no_input_streak == 0


def test_m4c_noinput_001_n07_multiple_utterances_does_not_change_streak() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult(
        "listen", "error", None, {"asr_error_code": "MULTIPLE_UTTERANCES"}), streak=1)
    response = sm._m4c_no_input_response()
    assert response is not None
    assert response.action_payload == {"text": "請一次只說一句。"}
    assert response.post_action_route == "KEEP_NEXT"
    assert sm._session is not None and sm._session.no_input_streak == 1


@pytest.mark.parametrize("code", ["INFERENCE_REJECTED", "INVALID_FRAME", "BACKEND_FAILURE"])
def test_m4c_noinput_001_n08_n10_system_fault_is_not_retry(code) -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "error", None, {"asr_error_code": code}), streak=1)
    assert sm._m4c_no_input_response() is None
    assert sm._session is not None and sm._session.no_input_streak == 1


@pytest.mark.parametrize("code", ["NO_SPEECH", "MULTIPLE_UTTERANCES"])
def test_m4c_noinput_001_n11_listener_preserves_only_stable_code(code) -> None:
    class Audio:
        def frames(self):
            async def values():
                yield b"\x00\x00"
            return values()

    class ASR:
        ready_for_next = True
        async def start(self): pass
        async def stop(self): pass
        async def abort(self): pass
        async def force_abort(self): raise AssertionError
        async def transcribe(self, frames):
            async for _ in frames:
                break
            raise AdapterRejected("PRIVATE NATIVE DETAIL", code=code)

    async def run():
        bus = EventBus()
        facts = []
        async def capture(event):
            facts.append(event)
        bus.subscribe(PerceptionResult, capture)
        listen = Listen(audio_input=Audio(), asr=ASR(), bus=bus)
        await listen.perceive("private-session", 1, 4, 1)
        assert len(facts) == 1
        assert facts[0].extra == {"asr_error_code": code}
        assert "PRIVATE" not in str(facts[0].extra)
    asyncio.run(run())
