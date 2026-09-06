"""Bounded process-group ownership and strict single-flight measurement RPC."""
from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import select
import signal
import subprocess
import threading
import time

from poc_llm.harness.mva_surface import canonical_bytes


class RunError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


SHUTDOWN_TIMEOUT_S = 10
PROCESS_WAIT_S = 2


class Child:
    def __init__(self, command: list[str], *, cwd: str, env: dict):
        self.process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b""
        self.ticket = 0
        self.pending = False
        self.abort_timers = []
        self.write_lock = threading.Lock()
        os.set_blocking(self.process.stdin.fileno(), False)

    @property
    def pid(self):
        return self.process.pid

    def owners(self) -> list[int]:
        if Path("/proc/self/stat").exists():
            owners = []
            for path in Path("/proc").glob("[0-9]*/stat"):
                try:
                    fields = path.read_text().rsplit(")", 1)[1].split()
                    if int(fields[2]) == self.pid:
                        owners.append(int(path.parent.name))
                except (FileNotFoundError, ProcessLookupError):
                    continue
            return sorted(owners)
        result = subprocess.run(["ps", "-axo", "pid=,pgid="], capture_output=True, text=True, timeout=3, check=True)
        return sorted(int(line.split()[0]) for line in result.stdout.splitlines()
                      if int(line.split()[1]) == self.pid)

    def send(self, request):
        data = canonical_bytes(request) + b"\n"
        if len(data) > 65536:
            raise RunError("PROTOCOL_ERROR")
        if not self.write_lock.acquire(timeout=1):
            raise RunError("PROTOCOL_ERROR")
        try:
            deadline = time.monotonic() + 1
            pending = memoryview(data)
            while pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([], [self.process.stdin], [], remaining)[1]:
                    raise RunError("TIMEOUT")
                try:
                    pending = pending[os.write(self.process.stdin.fileno(), pending):]
                except BlockingIOError:
                    continue
        except (OSError, ValueError):
            raise RunError("PROTOCOL_ERROR") from None
        finally:
            self.write_lock.release()

    def receive(self, timeout: float, monitor=lambda: None):
        # Keep native work bounded even when a resource probe stalls the main thread.
        expired = threading.Event()

        def force_abort():
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass

        def expire():
            expired.set()
            abort = threading.Timer(2, force_abort)
            abort.daemon = True
            self.abort_timers.append(abort)
            abort.start()
            try:
                self.send({"op": "CANCEL"})
            except (OSError, RunError):
                pass

        watchdog = threading.Timer(max(0, timeout), expire)
        watchdog.daemon = True
        watchdog.start()
        try:
            value = self._receive(timeout, monitor)
            if expired.is_set():
                raise RunError("TIMEOUT")
            return value
        finally:
            watchdog.cancel()
            watchdog.join()

    def _receive(self, timeout: float, monitor):
        deadline = time.monotonic() + timeout
        while True:
            monitor()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RunError("TIMEOUT")
            if b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                try:
                    value = json.loads(line)
                    canonical_bytes(value)
                    if not isinstance(value, dict) or "terminal" not in value:
                        raise ValueError()
                    return value
                except (ValueError, TypeError):
                    raise RunError("PROTOCOL_ERROR") from None
            if self.selector.select(min(0.1, remaining)):
                data = os.read(self.process.stdout.fileno(), 65536)
                if not data:
                    raise RunError("PROTOCOL_ERROR")
                self.buffer += data
                if len(self.buffer) > 65536:
                    raise RunError("PROTOCOL_ERROR")

    def call(self, op, *, timeout=30, monitor=lambda: None, **kwargs):
        if self.pending:
            raise RunError("PROTOCOL_ERROR")
        self.pending = True
        self.ticket += 1
        try:
            self.send({"op": op, "ticket": self.ticket, **kwargs})
            response = self.receive(timeout, monitor)
            if response.get("ticket") != self.ticket:
                raise RunError("PROTOCOL_ERROR")
            return response
        finally:
            self.pending = False

    def cleanup(self) -> dict:
        cooperative = False
        try:
            if self.process.poll() is None:
                # Releasing a multi-gigabyte native Engine on Pi can exceed the RPC's
                # ordinary two-second convergence window. Keep it bounded, but allow
                # normal teardown to finish before escalating to process-group signals.
                reply = self.call("SHUTDOWN", timeout=SHUTDOWN_TIMEOUT_S)
                cooperative = reply["terminal"] == "SHUTDOWN_ACK"
                self.process.wait(timeout=PROCESS_WAIT_S)
            else:
                self.process.wait(timeout=0)
        except (RunError, OSError, subprocess.TimeoutExpired):
            pass
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.pid, sig)
            except ProcessLookupError:
                break
            except PermissionError:
                # Still reap the direct child; do not claim group cleanup without proof.
                self.process.send_signal(sig)
            try:
                self.process.wait(timeout=PROCESS_WAIT_S)
            except subprocess.TimeoutExpired:
                pass
        try:
            absent = not self.owners()
        except (OSError, subprocess.SubprocessError):
            absent = False
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()
        for timer in self.abort_timers:
            timer.cancel()
            timer.join()
        return {"status": "PASS" if absent else "FAIL", "owners_absent": absent,
                "alsa_owners_zero": None, "cooperative": cooperative,
                "exit_code": self.process.returncode}
