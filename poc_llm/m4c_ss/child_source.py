"""Bounded long-lived child protocol for raw LiteRT S2 streaming."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import json
import os
import selectors
import signal
import subprocess
import threading
import time
from typing import Any

from poc_llm.efficiency.raw_stream import RawStreamChunk, RawStreamError
from poc_llm.m4c_ss.s2 import S2Terminal, consume_raw_s2


class StreamingChildError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class StreamingChildRuntime:
    """Own one process group and one active generation at a time."""

    def __init__(
        self,
        command: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        startup_timeout_s: float = 120.0,
        generation_timeout_s: float = 30.0,
        max_codepoints: int = 24,
    ) -> None:
        if not command or startup_timeout_s <= 0 or generation_timeout_s <= 0:
            raise ValueError("INVALID_CHILD_CONFIG")
        self.command = list(command)
        self.cwd = cwd
        self.env = dict(env)
        self.startup_timeout_s = startup_timeout_s
        self.generation_timeout_s = generation_timeout_s
        self.max_codepoints = max_codepoints
        self._process: subprocess.Popen[bytes] | None = None
        self._selector: selectors.BaseSelector | None = None
        self._buffer = b""
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._active = False
        self._destroyed = False
        self._cancel_sent = False

    @property
    def pid(self) -> int | None:
        return None if self._process is None else self._process.pid

    def start(self) -> None:
        if self._process is not None or self._destroyed:
            raise StreamingChildError("CHILD_NOT_STARTABLE")
        process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            bufsize=0,
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            process.wait(timeout=2)
            raise StreamingChildError("CHILD_START_FAILED")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        self._process = process
        self._selector = selector
        try:
            ready = self._receive(self.startup_timeout_s)
            if ready != {"protocol": 1, "type": "READY"}:
                raise StreamingChildError("CHILD_PROTOCOL_ERROR")
        except BaseException:
            self.force_abort()
            raise

    def generate(
        self,
        request: dict[str, Any],
        on_safe_text: Callable[[str], None],
    ) -> S2Terminal:
        with self._state_lock:
            if self._process is None or self._destroyed or self._active:
                raise StreamingChildError("CHILD_UNAVAILABLE")
            self._active = True
            self._cancel_sent = False
        try:
            self._send({"protocol": 1, "op": "GENERATE", "request": request})

            def chunks():
                while True:
                    frame = self._receive(self.generation_timeout_s)
                    if frame.get("protocol") != 1:
                        raise RawStreamError("PROTOCOL_ERROR")
                    if set(frame) == {"protocol", "type", "text", "is_final"} and frame["type"] == "CHUNK":
                        if type(frame["text"]) is not str or type(frame["is_final"]) is not bool:
                            raise RawStreamError("PROTOCOL_ERROR")
                        yield RawStreamChunk(frame["text"], frame["is_final"])
                        if frame["is_final"]:
                            return
                        continue
                    if set(frame) == {"protocol", "type", "code"} and frame["type"] == "ERROR":
                        code = frame["code"]
                        if code not in {"CANCELLED", "NATIVE_FAILURE", "TOKEN_LIMIT"}:
                            code = "PROTOCOL_ERROR"
                        raise RawStreamError(code)
                    raise RawStreamError("PROTOCOL_ERROR")

            return consume_raw_s2(
                chunks(), on_safe_text=on_safe_text,
                max_codepoints=self.max_codepoints,
            )
        finally:
            with self._state_lock:
                self._active = False

    def cancel(self) -> None:
        with self._state_lock:
            if not self._active or self._cancel_sent or self._destroyed:
                return
            self._cancel_sent = True
        self._send({"protocol": 1, "op": "CANCEL"})

    def force_abort(self) -> None:
        process = self._process
        if process is None:
            self._destroyed = True
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            try:
                process.wait(timeout=2.0)
                break
            except subprocess.TimeoutExpired:
                continue
        self._destroyed = True
        with self._state_lock:
            self._active = False
        self._close_pipes()

    def close(self) -> None:
        process = self._process
        if process is None or self._destroyed:
            return
        with self._state_lock:
            if self._active:
                raise StreamingChildError("CHILD_BUSY")
        try:
            self._send({"protocol": 1, "op": "SHUTDOWN"})
            reply = self._receive(10.0)
            if reply != {"protocol": 1, "type": "SHUTDOWN_ACK"}:
                raise StreamingChildError("CHILD_PROTOCOL_ERROR")
            process.wait(timeout=2.0)
        except (OSError, subprocess.TimeoutExpired, StreamingChildError):
            self.force_abort()
            return
        self._destroyed = True
        self._close_pipes()

    def operation_idle(self) -> bool:
        with self._state_lock:
            return not self._active

    def process_group_absent(self) -> bool:
        process = self._process
        if process is None:
            return True
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        return False

    def _send(self, value: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise StreamingChildError("CHILD_UNAVAILABLE")
        payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        if len(payload) > 65_536:
            raise StreamingChildError("CHILD_PROTOCOL_ERROR")
        with self._write_lock:
            try:
                process.stdin.write(payload)
                process.stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as error:
                raise StreamingChildError("CHILD_UNAVAILABLE") from error

    def _receive(self, timeout_s: float) -> dict[str, Any]:
        process, selector = self._process, self._selector
        if process is None or process.stdout is None or selector is None:
            raise StreamingChildError("CHILD_UNAVAILABLE")
        deadline = time.monotonic() + timeout_s
        while True:
            if b"\n" in self._buffer:
                line, self._buffer = self._buffer.split(b"\n", 1)
                try:
                    value = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    raise StreamingChildError("CHILD_PROTOCOL_ERROR") from None
                if type(value) is not dict:
                    raise StreamingChildError("CHILD_PROTOCOL_ERROR")
                return value
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise StreamingChildError("CHILD_TIMEOUT")
            if not selector.select(remaining):
                raise StreamingChildError("CHILD_TIMEOUT")
            data = os.read(process.stdout.fileno(), 65_536)
            if not data:
                raise StreamingChildError("CHILD_UNAVAILABLE")
            self._buffer += data
            if len(self._buffer) > 65_536:
                raise StreamingChildError("CHILD_PROTOCOL_ERROR")

    def _close_pipes(self) -> None:
        process, selector = self._process, self._selector
        if selector is not None:
            selector.close()
        self._selector = None
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()


class ChildS2Source:
    def __init__(self, runtime: StreamingChildRuntime, request: dict[str, Any]) -> None:
        self.runtime = runtime
        self.request = dict(request)

    async def generate(
        self, on_safe_text: Callable[[str], Awaitable[None]],
    ) -> S2Terminal:
        loop = asyncio.get_running_loop()

        def emit(text: str) -> None:
            future = asyncio.run_coroutine_threadsafe(on_safe_text(text), loop)
            future.result()

        return await asyncio.to_thread(self.runtime.generate, self.request, emit)

    async def cancel(self) -> None:
        await asyncio.to_thread(self.runtime.cancel)

    async def force_abort(self) -> None:
        await asyncio.to_thread(self.runtime.force_abort)

    def operation_idle(self) -> bool:
        return self.runtime.operation_idle()
