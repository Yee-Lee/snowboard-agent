"""M2 production-composition session and process flows."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from sbd.cognition.llm import LLMGeneration, LLMGenerationMetrics
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted,
    ErrorOccurred,
    LLMResponse,
    PerceptionResult,
    ShutdownRequested,
    StateChanged,
)
from sbd.core.m2_composition import M2Composition
from sbd.core.resource_manager import ResourceManager
from sbd.core.state_manager import StateManager
from sbd.core.state_manager.convergence import (
    CancelTimeoutPolicy,
    DefaultSessionConverger,
)


def _generation(kind: str, payload: dict, next_perceptions: list[str]) -> LLMGeneration:
    return LLMGeneration({
        "action_kind": kind,
        "action_payload": payload,
        "next_perceptions": next_perceptions,
    }, _metrics())


def _metrics() -> LLMGenerationMetrics:
    return LLMGenerationMetrics(0.0, 1.0, 1, 1.0, 1, 1.0, 1)


@dataclass
class _App:
    bus: EventBus
    rm: ResourceManager
    sm: StateManager
    composition: M2Composition
    states: asyncio.Queue[StateChanged]
    facts: list[PerceptionResult | LLMResponse | ActionCompleted]
    errors: list[ErrorOccurred]

    async def wait_session(self) -> tuple[str, ...]:
        observed: list[str] = []
        while not observed or observed[-1] != "IDLE":
            event = await asyncio.wait_for(self.states.get(), 5.0)
            observed.append(event.new)
        await asyncio.wait_for(self.sm._inbox.join(), 5.0)
        return tuple(observed)

    async def shutdown(self) -> None:
        await self.bus.publish(ShutdownRequested())
        await asyncio.wait_for(self.sm.wait_stopped(), 5.0)
        await self.sm.stop()
        report = await self.rm.stop_all()
        assert report.failures == ()


async def _start_app(outcomes: tuple[LLMGeneration | Exception, ...]) -> _App:
    config = DEFAULT_CONFIG
    bus = EventBus()
    composition = M2Composition(llm_outcomes=outcomes)
    rm = ResourceManager(config, bus)
    converger = DefaultSessionConverger(
        timeouts=CancelTimeoutPolicy(
            abort_default_seconds=config.cancel.abort_timeout_seconds.default,
            force_abort_default_seconds=(
                config.cancel.force_abort_timeout_seconds.default
            ),
            abort_by_kind=config.cancel.abort_timeout_seconds.by_kind,
            force_abort_by_kind=config.cancel.force_abort_timeout_seconds.by_kind,
        )
    )
    sm = StateManager(
        config,
        bus,
        rm.catalog,
        converger=converger,
        recovery=rm,
        action_validator=composition.action_validator,
    )
    rm.set_state_manager(sm)
    composition(rm, bus, config)
    states: asyncio.Queue[StateChanged] = asyncio.Queue()
    facts: list[PerceptionResult | LLMResponse | ActionCompleted] = []
    errors: list[ErrorOccurred] = []

    async def state(event: StateChanged) -> None:
        states.put_nowait(event)

    async def fact(
        event: PerceptionResult | LLMResponse | ActionCompleted,
    ) -> None:
        facts.append(event)

    async def error(event: ErrorOccurred) -> None:
        errors.append(event)

    bus.subscribe(StateChanged, state, name="test.m2.state")
    bus.subscribe(PerceptionResult, fact, name="test.m2.perception")
    bus.subscribe(LLMResponse, fact, name="test.m2.reason")
    bus.subscribe(ActionCompleted, fact, name="test.m2.action")
    bus.subscribe(ErrorOccurred, error, name="test.m2.error")
    await sm.start()
    await rm.start()
    return _App(bus, rm, sm, composition, states, facts, errors)


def test_m2_flow_001_button_two_turn_speak_then_rest() -> None:
    async def run() -> None:
        app = await _start_app((
            _generation("speak", {"text": "hello"}, ["listen"]),
            _generation("rest", {}, []),
        ))
        try:
            assert app.composition.button is not None
            await app.composition.button.emit()
            states = await app.wait_session()
            assert states == (
                "WAKE",
                "PERCEPTION",
                "THINK",
                "ACTION",
                "PERCEPTION",
                "THINK",
                "ACTION",
                "IDLE",
            )
            assert [type(fact) for fact in app.facts] == [
                PerceptionResult,
                LLMResponse,
                ActionCompleted,
                PerceptionResult,
                LLMResponse,
                ActionCompleted,
            ]
            session_ids = {fact.session_id for fact in app.facts}
            assert len(session_ids) == 1
            assert [(fact.turn_id, fact.correlation_id) for fact in app.facts] == [
                (1, 1),
                (1, 2),
                (1, 3),
                (2, 4),
                (2, 5),
                (2, 6),
            ]
            assert app.errors == []
            assert app.sm._in_flight == {} and app.sm._session is None
        finally:
            await app.shutdown()

    asyncio.run(run())


def test_m2_flow_002_external_message_read_once_action_then_rest() -> None:
    async def run() -> None:
        app = await _start_app((
            _generation("speak", {"text": "received"}, ["read"]),
            _generation("rest", {}, []),
        ))
        try:
            source = app.composition.external_message
            assert source is not None and source.is_available()
            message_id = await source.ingest(
                channel="fixture",
                text="private external body",
                metadata={"index": 1},
            )
            states = await app.wait_session()
            assert states == (
                "WAKE",
                "PERCEPTION",
                "THINK",
                "ACTION",
                "PERCEPTION",
                "THINK",
                "ACTION",
                "IDLE",
            )
            reads = [
                fact for fact in app.facts
                if isinstance(fact, PerceptionResult) and fact.kind == "read"
            ]
            assert len(reads) == 2
            assert reads[0].status == "ok"
            assert reads[0].text == "private external body"
            assert reads[0].extra["message_ids"] == (message_id,)
            assert reads[1].status == "timeout" and reads[1].text is None
            assert sum(
                message_id in fact.extra.get("message_ids", ())
                for fact in reads
            ) == 1
            assert app.errors == []
            assert app.sm._in_flight == {} and app.sm._read_open is None
        finally:
            await app.shutdown()

    asyncio.run(run())


def test_m2_flow_008_default_process_sigint_exits_zero_from_idle() -> None:
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    process = subprocess.Popen(
        [sys.executable, "-m", "sbd.main"],
        cwd=root,
        env=env,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stderr is not None
    output: Queue[str] = Queue()

    def read_stderr() -> None:
        assert process.stderr is not None
        for line in iter(process.stderr.readline, ""):
            output.put(line)
        process.stderr.close()

    reader = Thread(target=read_stderr, daemon=True)
    reader.start()
    captured: list[str] = []
    try:
        deadline = time.monotonic() + 10.0
        ready = False
        while time.monotonic() < deadline:
            try:
                line = output.get(timeout=0.1)
            except Empty:
                if process.poll() is not None:
                    break
                continue
            captured.append(line)
            if "M2 runtime ready state=IDLE" in line:
                ready = True
                break
        assert ready, "default M2 process did not reach IDLE: " + "".join(captured)
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=5.0) == 0
        reader.join(timeout=1.0)
        while not output.empty():
            captured.append(output.get_nowait())
        combined = "".join(captured)
        assert "Startup failed" not in combined
        assert "Runtime fatal" not in combined
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_m2_flow_004_bad_llm_fallback_continues_to_rest() -> None:
    async def run() -> None:
        app = await _start_app((
            LLMGeneration({"invalid": "bad-json-raw-secret"}, _metrics()),
            _generation("rest", {}, []),
        ))
        try:
            assert app.composition.button is not None
            await app.composition.button.emit()
            states = await app.wait_session()
            assert states == (
                "WAKE",
                "PERCEPTION",
                "THINK",
                "ACTION",
                "PERCEPTION",
                "THINK",
                "ACTION",
                "IDLE",
            )
            responses = [
                fact for fact in app.facts
                if isinstance(fact, LLMResponse)
            ]
            assert [response.action_kind for response in responses] == [
                "speak",
                "rest",
            ]
            assert responses[0].next_perceptions == ("listen",)
            assert "raw-secret" not in repr(responses)
            assert app.errors == []
        finally:
            await app.shutdown()

    asyncio.run(run())
