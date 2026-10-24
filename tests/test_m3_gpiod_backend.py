"""Host seam tests for libgpiod 2.x event-loop integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace

from sbd.core.config.models import GPIOConfig
from sbd.core.gpio.gpiod.driver import GpiodGPIO


class Request:
    next_fd = 100
    def __init__(self, pin):
        self.fd = Request.next_fd; Request.next_fd += 1
        self.pin = pin; self.events = []; self.released = False; self.value = None
    def read_edge_events(self): values, self.events = self.events, []; return values
    def release(self): self.released = True
    def set_value(self, pin, value): self.value = value


class FakeLoop:
    def __init__(self, real): self.real = real; self.readers = {}
    def add_reader(self, fd, callback, *args): self.readers[fd] = (callback, args)
    def remove_reader(self, fd): self.readers.pop(fd, None); return True


def _module(requests):
    line = SimpleNamespace(
        Edge=SimpleNamespace(RISING=1, FALLING=2, BOTH=3),
        Direction=SimpleNamespace(INPUT=1, OUTPUT=2),
        Clock=SimpleNamespace(MONOTONIC=1),
        Value=SimpleNamespace(ACTIVE=1, INACTIVE=0),
    )
    def request_lines(path, config, **kwargs):
        request = Request(next(iter(config))); requests.append(request); return request
    return SimpleNamespace(
        line=line, LineSettings=lambda **kwargs: kwargs, request_lines=request_lines,
        is_gpiochip_device=lambda path: path == "/dev/gpiochip0",
        EdgeEvent=SimpleNamespace(Type=SimpleNamespace(RISING_EDGE=1, FALLING_EDGE=2)),
    )


def test_gpiod_backend_fd_events_output_and_cleanup() -> None:
    async def scenario():
        requests, events = [], []
        gpio = GpiodGPIO(GPIOConfig(driver="gpiod"), gpiod_module=_module(requests))
        await gpio.start()
        real_loop = gpio._loop
        fake_loop = FakeLoop(real_loop)
        gpio._loop = fake_loop
        async def callback(event): events.append(event)
        await gpio.register_input(5, "both", callback, debounce_ms=20)
        request = requests[-1]
        request.events.append(SimpleNamespace(event_type=1, line_offset=5, timestamp_ns=1_250_000_000))
        callback_fn, args = fake_loop.readers[request.fd]
        callback_fn(*args)
        await asyncio.gather(*tuple(gpio._callback_tasks))
        assert [(event.pin, event.edge, event.at) for event in events] == [(5, "rising", 1.25)]
        await gpio.configure_output(10, initial=False)
        await gpio.set_output(10, True)
        assert requests[-1].value == 1
        await gpio.unregister(5); await gpio.unregister(5)
        await gpio.stop(); await gpio.stop()
        assert all(request.released for request in requests)
    asyncio.run(scenario())

def test_gpiod_backend_zero_debounce_omitted() -> None:
    async def scenario():
        requests = []
        module = _module(requests)
        gpio = GpiodGPIO(GPIOConfig(driver="gpiod"), gpiod_module=module)
        await gpio.start()
        gpio._loop = FakeLoop(gpio._loop)

        # Capture the kwargs passed to LineSettings
        captured_settings = []
        original_line_settings = module.LineSettings

        def spy_line_settings(**kwargs):
            captured_settings.append(kwargs)
            return original_line_settings(**kwargs)

        module.LineSettings = spy_line_settings

        # Test with debounce_ms=0 (the default if omitted)
        await gpio.register_input(5, "both", lambda e: None, debounce_ms=0)
        assert "debounce_period" not in captured_settings[-1]

        # Test with debounce_ms>0
        await gpio.register_input(6, "both", lambda e: None, debounce_ms=50)
        assert captured_settings[-1]["debounce_period"] == timedelta(milliseconds=50)

        await gpio.stop()
    asyncio.run(scenario())
