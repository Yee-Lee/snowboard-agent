"""Deterministic v3 fake runtime plus actual subprocess entry for product tests."""
from __future__ import annotations
import asyncio
import json
import os
import signal
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sbd.cognition.llm_child_protocol import ProtocolLedger
from sbd.cognition.litert_lm.worker import WorkerSession, run

class Runtime:
    def __init__(self):
        self.history = None
        self.kv = 0
        self.opens = self.closes = self.sends = self.cancels = 0
        self.user_tokens = 2
        self.incremental = 84
        self.prefill = 84
        self.output = '{"text":"你好","end":false}'
        self.generation_release = None
        self.cancel_raises = False
        self.scratch = None
        self.scrubs = 0
        self.render_calls = []

    def open_conversation(self):
        assert self.history is None
        self.history = []
        self.kv = 0
        self.opens += 1

    def measure(self, text):
        assert self.history is not None
        self.scratch = "rendered:" + text
        self.render_calls.append("measure")
        return dict(user_tokens=self.user_tokens, current_kv_tokens=self.kv,
                    rendered_incremental_tokens=self.incremental,
                    runtime_prefill_tokens=self.prefill,
                    output_reserve_tokens=128, engine_context_tokens=1024)

    def generate(self, text):
        assert self.history is not None
        if self.generation_release is not None:
            self.generation_release.wait()
        if self.cancel_raises and self.cancels:
            from sbd.cognition.litert_lm.worker import WorkerCancelled
            raise WorkerCancelled()
        self.sends += 1
        self.history.append(text)
        self.kv += self.incremental + 6
        return self.output, 6, self.kv, self.prefill

    def close_conversation(self):
        assert self.history is not None
        self.history.clear()
        self.history = None
        self.kv = 0
        self.closes += 1
        self.scratch = None

    def scrub_ticket(self):
        from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
        assert self.history is not None
        before = self.kv
        self.scratch = "rendered:" + TICKET_SCRUB_TEXT
        self.render_calls.append("scrub")
        self.scrubs += 1
        assert self.kv == before

    def cancel(self):
        self.cancels += 1
        if self.generation_release is not None:
            self.generation_release.set()

    def clear_pending_cancel(self):
        pass

    def close(self):
        assert self.history is None


def product_lock():
    from sbd.cognition.litert_lm.lock import LLMArtifactLock, profile_digest
    lock = LLMArtifactLock.load(ROOT / "requirements/m4b/llm-artifacts.json")
    profile = json.loads((ROOT / "requirements/m4b/product-profile.json").read_text())
    profile.update(profile_stage="release", min_mem_available_speak_bytes=100,
                   min_mem_available_generate_bytes=200,
                   measurement_evidence_locator="tests/public-memory-fixture")
    profile["profile_sha256"] = profile_digest(profile)
    return replace(lock, identity=lock.ready_identity(profile), product_profile=profile)


class Sampler:
    def __init__(self):
        self.calls = 0
        self.available = 1000
        self.failure = False

    def sample(self, *, child_pid, child_pgid):
        from sbd.cognition.litert_lm.resource import ProcessResource, SystemResourceSample
        self.calls += 1
        if self.failure:
            raise RuntimeError("private sampler canary")
        return SystemResourceSample(self.calls, (
            ProcessResource(1, "core", 1, 10, 20, 0.1, 1),
            ProcessResource(2, frozenset({"vad", "asr"}), 1, 10, 20, 0.1, 1),
            ProcessResource(3, "tts", 1, 10, 20, 0.1, 1),
            ProcessResource(child_pid, "llm", 1, 10, 20, 0.1, 1),
        ), 2000, self.available, 0, 0, 30.0, 0)


class Child:
    """Barriers hold completed native work before releasing the terminal."""
    def __init__(self, lock, epoch):
        self.pid = self.pgid = 100 + epoch
        self.lock = lock
        self.runtime = Runtime()
        self.session = WorkerSession(self.runtime)
        self.queue = asyncio.Queue()
        self.commands = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()
        self.terminated = self.stopped = 0
        self.pending = None
        self.transform = lambda event: event

    async def start(self):
        return {"protocol": 3, "event": "READY", **self.lock.identity.fields,
                "pid": self.pid, "pgid": self.pgid}

    async def send(self, frame):
        frame = dict(frame)
        self.commands.append({key: value for key, value in frame.items() if key != "text"})
        self.session.ledger.command(frame)
        self.entered.set()
        if frame["op"] == "CANCEL":
            self.runtime.cancel()
            operation = self.session.ledger.active["op"]
            event = {"protocol": 3, "event": "CANCELLED", "request_id": frame["request_id"],
                     "operation": operation, "request_terminal_proven": True,
                     "operation_cleanup_proven": operation != "CLOSE", "engine_usable": True,
                     "conversation_state": {"OPEN": "none", "MEASURE": "ready",
                         "GENERATE": "tainted", "CLOSE": "tainted"}[operation]}
            if operation == "OPEN":
                self.runtime.close_conversation()
            if operation == "MEASURE":
                try:
                    self.runtime.scrub_ticket()
                except BaseException:
                    event.update(operation_cleanup_proven=False, engine_usable=False,
                                 conversation_state="tainted")
            self.pending = [event]
            self.release.set()
            return
        self.pending = self.session.execute(frame)
        frame.pop("text", None)
        if self.release.is_set():
            await self._release_events()
        else:
            async def release_events():
                await self.release.wait()
                await self._release_events()
            asyncio.create_task(release_events())

    async def _release_events(self):
        events, self.pending = self.pending, None
        for event in events or ():
            if event.get("event") == "CANCELLED" and event.get("operation_cleanup_proven") is not True:
                self.session.ledger.state = "DESTROYED"
            else:
                self.session.ledger.event(event)
            transformed = self.transform(event)
            for frame in transformed if type(transformed) is list else [transformed]:
                await self.queue.put(frame)

    async def receive(self):
        if self.pending is not None:
            await self.release.wait()
            await self._release_events()
        return await self.queue.get()

    async def stop(self):
        self.stopped += 1
        assert self.runtime.history is None

    async def force_terminate(self):
        self.terminated += 1
        self.pending = None
        self.release.set()
        if self.runtime.history is not None:
            self.runtime.close_conversation()
        # A real process exit destroys its protocol owners as well as native
        # Conversation storage. Keep the in-process double's observable state
        # faithful, including a scrub failure before ticket invalidation.
        self.session.ledger = ProtocolLedger()
        self.session.ledger.state = "DESTROYED"
        while not self.queue.empty():
            self.queue.get_nowait()


def adapter_fixture():
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter
    from sbd.core.config.models import LLMConfig
    from sbd.core.resource_manager.models import RecoveryTicket
    children, tickets = [], []
    sampler = Sampler()
    def factory(cfg, lock, epoch):
        child = Child(lock, epoch)
        children.append(child)
        return child
    def schedule(keys):
        ticket = RecoveryTicket(len(tickets) + 1, keys)
        tickets.append(ticket)
        return ticket
    async def wait(ticket):
        await adapter.rebuild()
    adapter = LiteRTLMAdapter(LLMConfig(), lock=product_lock(), schedule_recovery=schedule,
                             wait_recovery=wait, resource_sampler=sampler, child_factory=factory)
    return adapter, children, tickets, sampler


from sbd.cognition.litert_lm.adapter import SubprocessLLMChild
from sbd.cognition.llm_child_protocol import MAX_CONTROL_BYTES, read_frame


class ProcessChild(SubprocessLLMChild):
    """Real PID=PGID fake sharing production I/O and termination implementation."""
    def __init__(self, cfg, lock, epoch, *, options=()):
        super().__init__(cfg, lock, epoch)
        self.options = options

    async def start(self):
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-B", str(Path(__file__).resolve()), *self.options,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, start_new_session=True,
            limit=MAX_CONTROL_BYTES + 1)
        self.pid = self.pgid = self._process.pid
        return await asyncio.wait_for(read_frame(self._process.stdout), 5)


if __name__ == "__main__":
    lock = product_lock()
    if "--ignore-term" in sys.argv:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if "--descendant" in sys.argv:
        import subprocess
        read_fd, write_fd = os.pipe()
        descendant = subprocess.Popen([sys.executable, "-c",
            "import os,signal,threading; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            f"os.write({write_fd},b'R'); os.close({write_fd}); threading.Event().wait()"],
            pass_fds=(write_fd,))
        os.close(write_fd)
        assert os.read(read_fd, 1) == b"R"
        os.close(read_fd)
    ready = {"protocol": 3, "event": "READY", **lock.identity.fields,
             "pid": os.getpid(), "pgid": os.getpgrp()}
    runtime = Runtime()
    if "--hold-measure" in sys.argv:
        import threading
        measure_release = threading.Event()
        original_measure, original_cancel = runtime.measure, runtime.cancel
        def held_measure(text):
            counts = original_measure(text)
            measure_release.wait()
            return counts
        def cancel_measure():
            original_cancel()
            measure_release.set()
        runtime.measure, runtime.cancel = held_measure, cancel_measure
    if "--discard-scrub-fails" in sys.argv:
        def fail_scrub():
            raise RuntimeError("private scrub failure")
        runtime.scrub_ticket = fail_scrub
    if "--discard-bad-proof" in sys.argv or "--discard-lost-ack" in sys.argv:
        from sbd.cognition.litert_lm import worker
        original_write = worker._write
        def alter_discard(frame):
            if frame.get("event") == "TICKET_DISCARDED":
                if "--discard-lost-ack" in sys.argv:
                    import threading
                    threading.Event().wait()
                frame = dict(frame, private_input_erased=False)
            original_write(frame)
        worker._write = alter_discard
    if "--hold-generate" in sys.argv:
        import threading
        runtime.generation_release = threading.Event()
        runtime.cancel_raises = "--cancel-raises" in sys.argv
    try:
        status = run(runtime, ready)
    except BaseException:
        status = 2
    os._exit(status)
