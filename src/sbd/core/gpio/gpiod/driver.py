"""Event-loop-owned libgpiod 2.x backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from sbd.core.config.models import GPIOConfig
from sbd.core.gpio.base import Edge, GPIOCallback, GPIOEvent


@dataclass(slots=True)
class _Input:
    request: object
    callback: GPIOCallback


class GpiodGPIO:
    def __init__(self, config: GPIOConfig, *, gpiod_module=None, logger=None) -> None:
        self._config = config
        self._gpiod = gpiod_module
        self._logger = logger or logging.getLogger(__name__)
        self._loop = None
        self._inputs: dict[int, _Input] = {}
        self._outputs: dict[int, object] = {}
        self._callback_tasks: set[asyncio.Task[None]] = set()
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        if self._gpiod is None:
            import gpiod
            self._gpiod = gpiod
        if not self._gpiod.is_gpiochip_device(self._config.chip):
            raise RuntimeError("configured GPIO chip is unavailable")
        self._loop = asyncio.get_running_loop()
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return
        for item in tuple(self._inputs.values()):
            self._loop.remove_reader(item.request.fd)
            item.request.release()
        for request in tuple(self._outputs.values()):
            request.release()
        self._inputs.clear()
        self._outputs.clear()
        if self._callback_tasks:
            await asyncio.gather(*tuple(self._callback_tasks), return_exceptions=True)
        self._callback_tasks.clear()
        self._started = False
        self._loop = None

    async def register_input(
        self, pin: int, edge: Edge, callback: GPIOCallback, debounce_ms: int = 0
    ) -> None:
        self._require_started()
        self._require_free(pin)
        edges = {
            "rising": self._gpiod.line.Edge.RISING,
            "falling": self._gpiod.line.Edge.FALLING,
            "both": self._gpiod.line.Edge.BOTH,
        }
        if edge not in edges or debounce_ms < 0 or not callable(callback):
            raise ValueError("invalid GPIO input registration")
        pin_config = next((value for value in self._config.pins.values() if value.pin == pin), None)
        settings = self._gpiod.LineSettings(
            direction=self._gpiod.line.Direction.INPUT,
            edge_detection=edges[edge],
            active_low=pin_config.active_low if pin_config else False,
            debounce_period=timedelta(milliseconds=debounce_ms),
            event_clock=self._gpiod.line.Clock.MONOTONIC,
        )
        request = self._gpiod.request_lines(
            self._config.chip, config={pin: settings},
            consumer="snowboard-agent", event_buffer_size=16,
        )
        self._inputs[pin] = _Input(request, callback)
        self._loop.add_reader(request.fd, self._read_ready, pin)

    async def unregister(self, pin: int) -> None:
        item = self._inputs.pop(pin, None)
        if item is not None:
            self._loop.remove_reader(item.request.fd)
            item.request.release()
        output = self._outputs.pop(pin, None)
        if output is not None:
            output.release()

    async def configure_output(self, pin: int, initial: bool = False) -> None:
        self._require_started()
        self._require_free(pin)
        if type(initial) is not bool:
            raise ValueError("GPIO output value must be bool")
        active = self._gpiod.line.Value.ACTIVE
        inactive = self._gpiod.line.Value.INACTIVE
        settings = self._gpiod.LineSettings(
            direction=self._gpiod.line.Direction.OUTPUT,
            output_value=active if initial else inactive,
        )
        self._outputs[pin] = self._gpiod.request_lines(
            self._config.chip, config={pin: settings},
            consumer="snowboard-agent", output_values={pin: active if initial else inactive},
        )

    async def set_output(self, pin: int, value: bool) -> None:
        if type(value) is not bool or pin not in self._outputs:
            raise ValueError("GPIO output pin is not configured or value is invalid")
        native = self._gpiod.line.Value.ACTIVE if value else self._gpiod.line.Value.INACTIVE
        self._outputs[pin].set_value(pin, native)

    def _read_ready(self, pin: int) -> None:
        item = self._inputs.get(pin)
        if item is None:
            return
        for event in item.request.read_edge_events():
            edge = (
                "rising" if event.event_type == self._gpiod.EdgeEvent.Type.RISING_EDGE
                else "falling"
            )
            task = asyncio.create_task(
                self._run_callback(item.callback, GPIOEvent(event.line_offset, edge, event.timestamp_ns / 1e9))
            )
            self._callback_tasks.add(task)
            task.add_done_callback(self._callback_tasks.discard)

    async def _run_callback(self, callback: GPIOCallback, event: GPIOEvent) -> None:
        try:
            await callback(event)
        except Exception:
            self._logger.exception("GPIO callback failed pin=%s", event.pin)

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("GpiodGPIO has not started")

    def _require_free(self, pin: int) -> None:
        if pin in self._inputs or pin in self._outputs:
            raise ValueError("GPIO pin is already configured")
