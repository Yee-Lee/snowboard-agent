"""Tests for the Event Bus."""

import asyncio
import logging
from typing import Any

import pytest
from sbd.core.events import Event, ShutdownRequested, StateChanged, ErrorOccurred
from sbd.core.event_bus import EventBus, FatalDispatchError
from sbd.core.event_bus.bus import EventBus as EventBusImplementation


def test_bus_public_api_reexports_package_implementation() -> None:
    assert EventBus is EventBusImplementation
    assert EventBus.__module__ == "sbd.core.event_bus.bus"


def test_bus_001_exact_type_snapshot_token_nosubscriber(caplog: Any) -> None:
    async def async_test():
        bus = EventBus()
        received_state: list[Event] = []
        received_base: list[Event] = []

        async def on_state(event: Event) -> None:
            received_state.append(event)

        async def on_base(event: Event) -> None:
            received_base.append(event)

        # 1. exact concrete type matching
        # 4. Duplicate subscription rejected
        token = bus.subscribe(StateChanged, on_state)
        with pytest.raises(ValueError):
            bus.subscribe(StateChanged, on_state)

        # Different type same handler is fine
        token2 = bus.subscribe(ShutdownRequested, on_state)  # type: ignore

        with pytest.raises(TypeError):
            bus.subscribe(Event, on_base) # type: ignore

        event1 = StateChanged(old="IDLE", new="WAKE")

        with caplog.at_level(logging.WARNING):
            await bus.publish(event1)

        assert len(received_state) == 1
        assert received_state[0] is event1
        assert len(received_base) == 0 # Event base class doesn't catch subclass

        # token lifecycle
        bus.unsubscribe(token)
        bus.unsubscribe(token) # idempotent

        with caplog.at_level(logging.WARNING):
            await bus.publish(StateChanged(old="WAKE", new="PERCEPTION"))
        assert len(received_state) == 1 # unchanged (actually 1 WARNING due to no sub for StateChanged since token was removed)

        # snapshot isolation
        async def on_state_modify(ev: Event) -> None:
            received_state.append(ev)
            bus.unsubscribe(token_mod) # remove self during dispatch
            bus.subscribe(StateChanged, on_state) # add another during dispatch

        token_mod = bus.subscribe(StateChanged, on_state_modify)

        event2 = StateChanged(old="PERCEPTION", new="THINK")
        await bus.publish(event2)
        assert len(received_state) == 2 # on_state_modify ran

        # now the state is: on_state_modify is removed, on_state is added
        event3 = StateChanged(old="THINK", new="ACTION")
        await bus.publish(event3)
        assert len(received_state) == 3 # on_state ran

        # no subscriber warning
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            from sbd.core.events import InterruptRequested
            await bus.publish(InterruptRequested())
            assert len(caplog.records) > 0
            assert "No subscriber for event type" in caplog.text

    asyncio.run(async_test())


def test_bus_003_handler_failure_deferred_error() -> None:
    async def async_test():
        bus = EventBus()
        calls: list[str] = []

        async def handler1(ev: Event) -> None:
            calls.append("h1")
            raise ValueError("h1 error")

        async def handler2(ev: Event) -> None:
            calls.append("h2")

        async def handler3(ev: Event) -> None:
            calls.append("h3")
            # also publish manually to test deduplication
            await bus.publish(ErrorOccurred(where="manual", error="manual"))
            raise KeyError("h3 error")

        bus.subscribe(StateChanged, handler1, name="handler1")
        bus.subscribe(StateChanged, handler2, name="handler2")
        bus.subscribe(StateChanged, handler3, name="handler3")

        errors: list[ErrorOccurred] = []
        async def on_error(ev: ErrorOccurred) -> None:
            errors.append(ev)

        bus.subscribe(ErrorOccurred, on_error)

        await bus.publish(StateChanged(old="IDLE", new="WAKE"))

        assert calls == ["h1", "h2", "h3"]
        assert len(errors) == 3
        # First the manual one because it was published recursively during handler3
        # Wait, actually since publish is awaited in handler3, it finishes dispatching its own snapshot
        assert errors[0].where == "manual"
        # Then the fallbacks from the original dispatch
        assert errors[1].where == "bus.dispatch.handler1"
        assert errors[1].exception_type == "ValueError"
        assert errors[2].where == "bus.dispatch.handler3"
        assert errors[2].exception_type == "KeyError"

    asyncio.run(async_test())


def test_bus_004_cancelled_fatal_handoff() -> None:
    async def async_test():
        bus = EventBus()

        async def handler_cancel(ev: Event) -> None:
            raise asyncio.CancelledError()

        bus.subscribe(ShutdownRequested, handler_cancel)

        # CancelledError passthrough
        with pytest.raises(asyncio.CancelledError):
            await bus.publish(ShutdownRequested())

        # Fatal handoff
        async def error_handler_1(ev: ErrorOccurred) -> None:
            raise RuntimeError("error in error handler 1")

        async def error_handler_2(ev: ErrorOccurred) -> None:
            pass # should not run

        bus.subscribe(ErrorOccurred, error_handler_1)
        bus.subscribe(ErrorOccurred, error_handler_2)

        wait_task = asyncio.create_task(bus.wait_fatal())

        with pytest.raises(FatalDispatchError) as exc_info:
            await bus.publish(ErrorOccurred(where="test", error="test"))

        assert exc_info.value.root_cause.args[0] == "error in error handler 1"
        assert exc_info.value.event_type == "ErrorOccurred"

        # wait_fatal should also raise the same exception
        with pytest.raises(FatalDispatchError) as exc_info2:
            await wait_task

        assert exc_info.value is exc_info2.value
        assert exc_info.value.__cause__ is exc_info.value.root_cause

        # post-fatal behavior
        with pytest.raises(FatalDispatchError):
            await bus.publish(ShutdownRequested())

        # wait_fatal should still raise if called after
        with pytest.raises(FatalDispatchError) as exc_info3:
            await bus.wait_fatal()
        assert exc_info.value is exc_info3.value

    asyncio.run(async_test())


def test_bus_regression_concrete_kind_bound_method_and_canonical_name() -> None:
    async def run() -> None:
        bus = EventBus()
        errors: list[ErrorOccurred] = []

        class Handler:
            async def handle(self, event: StateChanged) -> None:
                raise RuntimeError("SENSITIVE_SENTINEL")

        async def observe(event: ErrorOccurred) -> None:
            errors.append(event)

        handler = Handler()
        bus.subscribe(ErrorOccurred, observe)
        for name, expected in (("Bad-Handler Name!!", "bad_handler_name"), ("123", "handler_123"), ("Ä-1", "handler_1")):
            token = bus.subscribe(StateChanged, handler.handle, name=name)
            with pytest.raises(ValueError):
                bus.subscribe(StateChanged, handler.handle)
            await bus.publish(StateChanged("IDLE", "WAKE"))
            assert errors[-1].where == f"bus.dispatch.{expected}"
            assert __import__("re").fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", errors[-1].where)
            bus.unsubscribe(token)

    asyncio.run(run())
