"""Async in-memory GPIO driver with debounce and callback isolation."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from sbd.core.gpio.base import Edge, GPIOCallback, GPIOEvent


@dataclass(slots=True)
class _InputRegistration:
    edge: Edge
    callback: GPIOCallback
    debounce_seconds: float
    last_at: float | None = None


class MockGPIO:
    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._inputs: dict[int, _InputRegistration] = {}
        self._outputs: dict[int, bool] = {}
        self._callback_tasks: set[asyncio.Task[None]] = set()
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        if self._callback_tasks:
            await asyncio.gather(*tuple(self._callback_tasks), return_exceptions=True)
        self._inputs.clear()
        self._outputs.clear()
        self._started = False

    async def register_input(
        self,
        pin: int,
        edge: Edge,
        callback: GPIOCallback,
        debounce_ms: int = 0,
    ) -> None:
        if pin in self._inputs or pin in self._outputs:
            raise ValueError("GPIO pin is already configured")
        if edge not in {"rising", "falling", "both"}:
            raise ValueError("unknown GPIO edge")
        if not callable(callback) or debounce_ms < 0:
            raise ValueError("invalid GPIO callback or debounce")
        self._inputs[pin] = _InputRegistration(
            edge=edge,
            callback=callback,
            debounce_seconds=debounce_ms / 1000.0,
        )

    async def unregister(self, pin: int) -> None:
        self._inputs.pop(pin, None)
        self._outputs.pop(pin, None)

    async def configure_output(self, pin: int, initial: bool = False) -> None:
        if pin in self._inputs or pin in self._outputs:
            raise ValueError("GPIO pin is already configured")
        if type(initial) is not bool:
            raise ValueError("GPIO output value must be bool")
        self._outputs[pin] = initial

    async def set_output(self, pin: int, value: bool) -> None:
        if pin not in self._outputs:
            raise ValueError("GPIO output pin is not configured")
        if type(value) is not bool:
            raise ValueError("GPIO output value must be bool")
        self._outputs[pin] = value

    async def simulate_event(
        self,
        pin: int,
        edge: str,
        *,
        at: float | None = None,
    ) -> bool:
        registration = self._inputs.get(pin)
        if registration is None:
            raise ValueError("GPIO input pin is not registered")
        if edge not in {"rising", "falling"}:
            raise ValueError("unknown GPIO event edge")
        now = time.monotonic() if at is None else at
        if registration.edge not in {edge, "both"}:
            return False
        if (
            registration.last_at is not None
            and now - registration.last_at < registration.debounce_seconds
        ):
            return False
        registration.last_at = now
        task = asyncio.create_task(
            self._run_callback(registration.callback, GPIOEvent(pin, edge, now))
        )
        self._callback_tasks.add(task)
        task.add_done_callback(self._callback_tasks.discard)
        return True

    async def wait_callbacks(self) -> None:
        if self._callback_tasks:
            await asyncio.gather(*tuple(self._callback_tasks), return_exceptions=True)

    def output_value(self, pin: int) -> bool:
        try:
            return self._outputs[pin]
        except KeyError as exc:
            raise ValueError("GPIO output pin is not configured") from exc

    async def _run_callback(self, callback: GPIOCallback, event: GPIOEvent) -> None:
        try:
            await callback(event)
        except Exception:
            self._logger.exception("GPIO callback failed pin=%s", event.pin)
