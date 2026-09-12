"""Parent ownership, v3 serialization, and SM-authorized planned recovery."""
from __future__ import annotations
import asyncio
import os
import shutil
import signal
import sys
import time
import tempfile
from contextlib import asynccontextmanager
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Protocol

from sbd.cognition.litert_lm.lock import LLMArtifactLock
from sbd.cognition.llm import (AdmissionSnapshot, TicketDiscardProof, GenerationMetrics, SemanticGeneration,
    LLMFatalError, ReplaceableGenerationFailure, MemoryAdmissionDenied,
    LLMResourceSampler, ScheduleRecovery, WaitRecovery)
from sbd.cognition.llm_child_protocol import (MAX_CONTROL_BYTES, PROTOCOL_VERSION,
    LLMProtocolError, ProtocolLedger, encode_frame, read_frame, parse_ready, require, digest)
from sbd.core.config.models import LLMConfig
from sbd.core.lifecycle import ForceAbortReport

RESOURCE_KEY = "backend.cognition.reasoner.llm"

@dataclass(frozen=True, slots=True)
class LLMTerminationEvidence:
    term_sent: bool
    kill_sent: bool
    waitpid_exit_code: int
    orphan_count: int

@dataclass(frozen=True, slots=True)
class LLMCancelEvidence:
    native_cancel_calls: int
    worker_joined: bool

class AdapterState(Enum):
    STOPPED = auto()
    AUTHENTICATING = auto()
    STARTING = auto()
    ENGINE_READY = auto()
    CONVERSATION_READY = auto()
    MEASURED = auto()
    DISCARDING = auto()
    GENERATING = auto()
    TAINTED = auto()
    RECYCLE_PENDING = auto()
    RECOVERING = auto()
    DESTROYED = auto()

class LLMChild(Protocol):
    pid: int
    pgid: int
    async def start(self) -> Mapping[str, object]: ...
    async def send(self, frame: Mapping[str, object]) -> None: ...
    async def receive(self) -> Mapping[str, object]: ...
    async def stop(self) -> None: ...
    async def force_terminate(self) -> None: ...

def isolated_child_environment(runtime_root: Path, source: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    for name in tuple(environment):
        if name in {"PYTHONPATH", "PYTHONHOME", "LD_PRELOAD"} or name.lower().endswith("_proxy"):
            environment.pop(name, None)
    environment.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "LD_LIBRARY_PATH": str(runtime_root / "litert_lm"),
    })
    return environment


class SubprocessLLMChild:
    """One process group and its bounded stdio/work-directory resources."""

    def __init__(self, cfg: LLMConfig, lock: LLMArtifactLock, generation: int, *, measurement_grant: Any = None) -> None:
        self._cfg = cfg
        self._lock = lock
        self._generation = generation
        self._measurement_grant = measurement_grant
        self._process: asyncio.subprocess.Process | None = None
        self._workdir: Path | None = None
        self.pid = 0
        self.pgid = 0
        self.termination_evidence: LLMTerminationEvidence | None = None
        self._stop_lock = asyncio.Lock()

    def clock_mapping_token(self) -> tuple[int, ...] | None:
        """Prove the live child shares this controller's Linux monotonic epoch."""
        if sys.platform != "linux" or time.get_clock_info("monotonic").implementation != "clock_gettime(CLOCK_MONOTONIC)":
            return None
        process = self._process
        if process is None or process.returncode is not None or process.pid != self.pid:
            return None
        try:
            proc = Path("/proc") / str(self.pid)
            before = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            local_ns = Path("/proc/self/ns/time").stat()
            child_ns = (proc / "ns/time").stat()
            after = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            if (before[19] != after[19] or after[0] == "Z"
                    or int(after[2]) != self.pgid or self.pgid != self.pid
                    or (local_ns.st_dev, local_ns.st_ino) != (child_ns.st_dev, child_ns.st_ino)):
                return None
            return (self.pid, int(after[19]), local_ns.st_dev, local_ns.st_ino)
        except (OSError, ValueError, IndexError):
            return None

    async def start(self) -> Mapping[str, object]:
        assert self._cfg.runtime_python is not None
        assert self._cfg.model_path is not None
        assert self._cfg.product_profile_path is not None
        runtime_root = self._cfg.runtime_python.parent.parent / "lib/python3.13/site-packages"
        worker_path = Path(__file__).with_name("worker.py").resolve()
        argv = [
            str(self._cfg.runtime_python), "-I", "-B", str(worker_path),
            "--model", str(self._cfg.model_path),
            "--product-profile", str(self._cfg.product_profile_path),
            "--runtime-root", str(runtime_root),
            "--artifact-lock", str(self._cfg.artifact_lock_path),
        ]
        if self._measurement_grant is not None:
            from sbd.cognition.litert_lm.measurement import MeasurementGrant
            require(type(self._measurement_grant) is MeasurementGrant, "measurement")
            self._measurement_grant.authorize_profile(self._lock.product_profile)
            argv.extend(self._measurement_grant.child_arguments())
        self._workdir = Path(tempfile.mkdtemp(prefix="m4b-llm-"))
        try:
            self._process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=self._workdir,
                env=isolated_child_environment(runtime_root),
                start_new_session=True,
                close_fds=True,
                limit=MAX_CONTROL_BYTES + 1,
            )
            self.pid = self._process.pid
            self.pgid = self.pid
            assert self._process.stdout is not None
            ready = await asyncio.wait_for(
                read_frame(self._process.stdout), self._cfg.child_ready_timeout_seconds
            )
            return ready
        except BaseException:
            await self.force_terminate()
            raise

    async def send(self, frame: Mapping[str, object]) -> None:
        if self._process is None or self._process.stdin is None or self._process.returncode is not None:
            raise LLMFatalError("child input is unavailable")
        self._process.stdin.write(encode_frame(frame))
        try:
            await self._process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as error:
            raise LLMFatalError("child input closed") from None

    async def receive(self) -> Mapping[str, object]:
        if self._process is None or self._process.stdout is None:
            raise LLMFatalError("child output is unavailable")
        return await read_frame(self._process.stdout)

    async def stop(self) -> None:
        async with self._stop_lock:
            process = self._process
            if process is None:
                await self._cleanup()
                return
            try:
                await self.send({"protocol": 3, "op": "SHUTDOWN"})
                frame = await asyncio.wait_for(self.receive(), self._cfg.child_terminate_timeout_seconds)
                if frame != {"protocol": 3, "event": "SHUTDOWN_ACK"}:
                    raise LLMProtocolError(stage="SHUTDOWN", field="$", reason="invalid acknowledgement")
                await asyncio.wait_for(
                    self._wait_process_group_exit(process, process.pid),
                    self._cfg.child_terminate_timeout_seconds,
                )
                if process.returncode != 0:
                    raise LLMFatalError("child exited nonzero")
            except BaseException:
                await self.force_terminate()
                raise
            await self._cleanup()

    async def force_terminate(self) -> None:
        process = self._process
        term_sent = False
        kill_sent = False
        if process is not None and (
            process.returncode is None or self._live_process_group_members(process.pid)
        ):
            try:
                os.killpg(process.pid, signal.SIGTERM)
                term_sent = True
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(
                    self._wait_process_group_exit(process, process.pid),
                    self._cfg.child_terminate_timeout_seconds,
                )
            except TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    kill_sent = True
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(
                        self._wait_process_group_exit(process, process.pid),
                        self._cfg.child_kill_wait_timeout_seconds,
                    )
                except TimeoutError as error:
                    raise LLMFatalError("child process-group exit could not be proven") from None
        if process is not None:
            await process.wait()
            members = self._live_process_group_members(process.pid)
            self.termination_evidence = LLMTerminationEvidence(
                term_sent=term_sent,
                kill_sent=kill_sent,
                waitpid_exit_code=int(process.returncode or 0),
                orphan_count=len(members),
            )
        await self._cleanup()

    @staticmethod
    def _live_process_group_members(pgid: int) -> set[int]:
        proc = Path("/proc")
        if not proc.is_dir():
            try:
                os.killpg(pgid, 0)
                return {pgid}
            except ProcessLookupError:
                return set()
        members: set[int] = set()
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
                if fields[0] != "Z" and int(fields[2]) == pgid:
                    members.add(int(entry.name))
            except (OSError, ValueError, IndexError):
                continue
        return members

    async def _wait_process_group_exit(
        self, process: asyncio.subprocess.Process, pgid: int,
    ) -> None:
        while process.returncode is None or self._live_process_group_members(pgid):
            await asyncio.sleep(0.01)
        await process.wait()

    async def _cleanup(self) -> None:
        process = self._process
        if process is not None:
            for stream in (process.stdin,):
                if stream is not None:
                    stream.close()
                    try:
                        await asyncio.wait_for(
                            stream.wait_closed(),
                            self._cfg.child_kill_wait_timeout_seconds,
                        )
                    except (TimeoutError, BrokenPipeError, ConnectionResetError):
                        pass
            self._process = None
        if self._workdir is not None:
            workdir = self._workdir
            try:
                shutil.rmtree(workdir)
            except FileNotFoundError:
                pass
            except OSError as error:
                raise LLMFatalError("child work-directory cleanup failed") from None
            if workdir.exists() or workdir.is_symlink():
                raise LLMFatalError("child work-directory cleanup failed")
            self._workdir = None



ChildFactory = Callable[[LLMConfig, LLMArtifactLock, int], LLMChild]

class _ConversationControl:
    """Dedicated SM facade; native generation is deliberately unavailable here."""
    def __init__(self, adapter):
        self._adapter = adapter

    @property
    def recovery_pending(self):
        return self._adapter.recovery_pending

    async def open_conversation(self, session_id, generation):
        return await self._adapter.open_conversation(session_id, generation)

    async def close_conversation(self, session_id, generation, reason):
        return await self._adapter.close_conversation(session_id, generation, reason)

    async def authorize_recovery(self, session_id, generation, proof):
        return await self._adapter.authorize_recovery(session_id, generation, proof)

    async def abort(self):
        return await self._adapter.abort()

    async def force_abort(self):
        return await self._adapter.force_abort()


class LiteRTLMAdapter:
    def __init__(self, cfg: LLMConfig, *, lock: LLMArtifactLock,
                 schedule_recovery: ScheduleRecovery, wait_recovery: WaitRecovery,
                 resource_sampler: LLMResourceSampler,
                 child_factory: ChildFactory = SubprocessLLMChild,
                 observer: Any = None, measurement_grant: Any = None) -> None:
        self._cfg, self._lock = cfg, lock
        self._schedule_recovery, self._wait_recovery = schedule_recovery, wait_recovery
        self._sampler, self._child_factory = resource_sampler, child_factory
        self._observer = observer
        self._measurement_grant = measurement_grant
        if measurement_grant is not None:
            from sbd.cognition.litert_lm.measurement import MeasurementGrant
            require(type(measurement_grant) is MeasurementGrant, "measurement")
            measurement_grant.authorize_profile(lock.product_profile)
        else:
            require(lock.product_profile["profile_stage"] == "release", "measurement")
        self._observation_generation = 0
        self._clock_token: tuple[int, ...] | None = None
        self._clock_mapped = False
        self._child: LLMChild | None = None
        self._issued_tickets: set[str] = set()
        self._ledger = ProtocolLedger(self._issued_tickets)
        self._epoch = 0
        self._operation_lock = asyncio.Lock()
        self._lock_owner: asyncio.Task | None = None
        self._reader_task: asyncio.Task | None = None
        self._destruction_task: asyncio.Task | None = None
        self._responses: asyncio.Queue = asyncio.Queue()
        self._operation_done = asyncio.Event()
        self._operation_done.set()
        self._pending: tuple[str, int] | None = None
        self._closed_proof: Any = None
        self._recovery_ticket: Any = None
        self._authorization: asyncio.Task | None = None
        self._previous_sample: Any = None
        self._atomic_interrupt = False
        self.state = AdapterState.STOPPED
        self.last_termination_evidence: LLMTerminationEvidence | None = None
        self.last_cancel_evidence: LLMCancelEvidence | None = None
        self.control = _ConversationControl(self)

    @property
    def operation_lock(self) -> asyncio.Lock:
        return self._operation_lock

    @asynccontextmanager
    async def serialized(self):
        task = asyncio.current_task()
        if self._lock_owner is task:
            yield
            return
        if self._operation_lock.locked():
            await self._destroy()
            raise LLMFatalError("BUSY")
        async with self._operation_lock:
            self._lock_owner = task
            try:
                yield
            except LLMFatalError:
                if self._child is not None:
                    await self._destroy()
                raise
            finally:
                self._lock_owner = None

    @property
    def recovery_pending(self) -> bool:
        return self._pending is not None

    @property
    def conversation_revision(self) -> int:
        return self._ledger.revision

    def assert_conversation(self, session_id: str, generation: int) -> None:
        require(type(session_id) is str and type(generation) is int and generation > 0, "identity")
        require(self.state not in {AdapterState.DESTROYED, AdapterState.STOPPED}, "state")
        require(self._ledger.claim == (session_id, generation), "identity")
        require(self._ledger.state in {"CONVERSATION_READY", "MEASURED"}, "state")

    async def start(self) -> None:
        async with self.serialized():
            require(self.state is AdapterState.STOPPED, "state")
            await self._start_replacement()

    async def _start_replacement(self) -> None:
        self.state = AdapterState.AUTHENTICATING
        if self._measurement_grant is not None:
            self._measurement_grant.authorize_profile(self._lock.product_profile)
        if self._lock.runtime_closure is not None:
            require(self._cfg.runtime_python is not None)
            self._lock.runtime_closure.verify_install(
                self._cfg.runtime_python.parent.parent / "lib/python3.13/site-packages")
            self._lock.verify_config_paths(self._cfg, allow_measurement=self._measurement_grant is not None)
        require(self._lock.identity is not None, "identity")
        self._epoch += 1
        self._destruction_task = None
        if self._measurement_grant is None:
            child = self._child_factory(self._cfg, self._lock, self._epoch)
        else:
            child = self._child_factory(self._cfg, self._lock, self._epoch,
                                        measurement_grant=self._measurement_grant)
        self._child = child
        self.state = AdapterState.STARTING
        try:
            ready = await asyncio.wait_for(child.start(), self._cfg.child_ready_timeout_seconds)
            parse_ready(ready, expected_identity=self._lock.identity, pid=child.pid, pgid=child.pgid)
            self._ledger = ProtocolLedger(self._issued_tickets)
            self._responses = asyncio.Queue()
            # Only rebuild reaches epoch > 1, after old PGID destruction and
            # fully authenticated new READY. Preserve system/non-LLM health
            # while rebasing the intentionally replaced LLM owner identity.
            rebase = getattr(self._sampler, "rebase_llm_owner", None)
            sample = rebase if self._epoch > 1 and callable(rebase) else self._sampler.sample
            self._previous_sample = sample(child_pid=child.pid, child_pgid=child.pgid)
            self._previous_sample.validate()
            if self._measurement_grant is not None:
                self._measurement_grant.check_sample(self._previous_sample)
            if self._observer is not None:
                self._observer.prompt(self._lock.product_profile)
                self._observer.memory(self._previous_sample, generation=0,
                                      lifecycle_point="engine_ready")
            self.state = AdapterState.ENGINE_READY
            self._reader_task = asyncio.create_task(self._read_responses(), name="llm-wire")
        except asyncio.CancelledError:
            await self._destroy()
            raise
        except BaseException:
            await self._destroy()
            raise LLMFatalError("LLM startup failed") from None

    async def _read_responses(self) -> None:
        child = self._child
        assert child is not None
        try:
            while True:
                frame = await child.receive()
                operation = self._ledger.active
                generating = operation is not None and operation["op"] == "GENERATE"
                terminal = self._ledger.event(frame)
                if generating and terminal:
                    prove = getattr(child, "clock_mapping_token", None)
                    after = prove() if callable(prove) else None
                    self._clock_mapped = self._clock_token is not None and self._clock_token == after
                self._responses.put_nowait(frame)
                if terminal and self._ledger.state == "STOPPED":
                    return
        except asyncio.CancelledError:
            raise
        except BaseException:
            await self._destroy()
            self._responses.put_nowait(LLMFatalError("LLM wire failure"))

    def _frame(self, op: str, session_id: str, generation: int, **extra: object) -> dict[str, object]:
        return {"protocol": 3, "op": op, "request_id": self._ledger.counter + 1,
                "session_id": session_id, "generation": generation, **extra}

    async def _request(self, frame: Mapping[str, object]) -> Mapping[str, object]:
        child = self._child
        require(child is not None and self.state is not AdapterState.DESTROYED, "state")
        try:
            if self._measurement_grant is not None and frame["op"] != "GENERATE":
                sample = self._sampler.sample(child_pid=child.pid, child_pgid=child.pgid)
                self._validate_sample(sample)
                self._measurement_grant.check_sample(sample)
                self._previous_sample = sample
            self._ledger.command(frame)
            self._atomic_interrupt = False
            self._operation_done.clear()
            if frame["op"] == "GENERATE":
                prove = getattr(child, "clock_mapping_token", None)
                self._clock_token = prove() if callable(prove) else None
                self._clock_mapped = False
            await child.send(frame)
            timeout = (self._cfg.generation_timeout_seconds if frame["op"] == "GENERATE"
                       else self._cfg.child_ready_timeout_seconds)
            if frame["op"] == "DISCARD_TICKET":
                timeout = self._cfg.terminal_grace_seconds
            async def terminal():
                while True:
                    event = await self._responses.get()
                    if isinstance(event, BaseException):
                        raise event
                    if event["event"] not in {"SAFE_TEXT", "CANCEL_DEFERRED"}:
                        return event
            expired = False
            try:
                event = await asyncio.wait_for(terminal(), timeout)
            except TimeoutError:
                expired = True
                if frame["op"] == "DISCARD_TICKET":
                    raise LLMFatalError("ticket disposal timed out") from None
                if self._ledger.active is not None and not self._ledger.cancelled:
                    cancel = {"protocol": 3, "op": "CANCEL", "request_id": frame["request_id"]}
                    self._ledger.command(cancel)
                    await child.send(cancel)
                event = await asyncio.wait_for(terminal(), self._cfg.terminal_grace_seconds)
            if event["event"] == "CANCELLED":
                self.last_cancel_evidence = LLMCancelEvidence(1, True)
                self._sync_state()
                if expired and frame["op"] == "GENERATE":
                    raise ReplaceableGenerationFailure("GENERATION_TIMEOUT")
                raise asyncio.CancelledError
            require(self.state is not AdapterState.DESTROYED, "state")
            self._sync_state()
            if self._atomic_interrupt:
                raise asyncio.CancelledError
            return event
        except ReplaceableGenerationFailure:
            raise
        except asyncio.CancelledError:
            # A validated cooperative terminal needs no forced destruction.
            if self._ledger.active is not None:
                await self._destroy()
            else:
                self._sync_state()
            raise
        except BaseException:
            await self._destroy()
            raise LLMFatalError("LLM operation failed") from None
        finally:
            self._operation_done.set()

    def _sync_state(self) -> None:
        if self._pending is not None:
            self.state = AdapterState.RECYCLE_PENDING
        elif self._ledger.state in AdapterState.__members__:
            self.state = AdapterState[self._ledger.state]

    def _validate_sample(self, sample: Any) -> None:
        validate = getattr(self._sampler, "validate_sample", None)
        if callable(validate):
            validate(sample, self._previous_sample)
        else:
            sample.validate(self._previous_sample)

    async def observe_memory(self, lifecycle_point: str) -> None:
        """Private lifecycle callback; never substitutes a partial owner sample."""
        if self._observer is None:
            return
        child = self._child
        require(child is not None, "state")
        try:
            sample = self._sampler.sample(child_pid=child.pid, child_pgid=child.pgid)
            self._validate_sample(sample)
            if self._measurement_grant is not None:
                self._measurement_grant.check_sample(sample)
            self._previous_sample = sample
            self._observer.memory(sample, generation=self._observation_generation,
                                  lifecycle_point=lifecycle_point)
        except BaseException:
            await self._destroy()
            raise LLMFatalError("MEMORY_SAMPLE_INVALID") from None

    async def open_conversation(self, session_id: str, generation: int):
        from sbd.core.state_manager.ports import ConversationReady, ConversationOpenRejected
        authorization = self._authorization
        if authorization is not None:
            await asyncio.shield(authorization)
        require(self._pending is None, "recovery")
        async with self.serialized():
            self._observation_generation = generation
            await self.observe_memory("conversation_preparation")
            event = await self._request(self._frame("OPEN", session_id, generation))
            self._closed_proof = None
            if event["event"] == "OPEN_REJECTED":
                return ConversationOpenRejected(session_id, generation, True, True)
            if self._observer is not None:
                self._observer.conversation_ready(generation)
            await self.observe_memory("conversation_ready")
            return ConversationReady(session_id, generation)

    async def measure(self, session_id: str, generation: int, text: str) -> AdmissionSnapshot:
        async with self.serialized():
            self.assert_conversation(session_id, generation)
            event = await self._request(self._frame("MEASURE", session_id, generation,
                text=text, input_sha256=digest(text), output_reserve_tokens=128))
            snapshot = AdmissionSnapshot(**{key: event[key] for key in AdmissionSnapshot.__dataclass_fields__})
            if self._observer is not None:
                self._observer.measured(snapshot)
            return snapshot

    async def generate(self, snapshot: AdmissionSnapshot, text: str) -> SemanticGeneration:
        from sbd.cognition.litert_lm.resource import memory_decision, MemoryDecision
        async with self.serialized():
            self.assert_conversation(snapshot.session_id, snapshot.generation)
            ticket = self._ledger.ticket
            require(ticket is not None and all(type(getattr(snapshot, key)) is type(ticket[key]) and getattr(snapshot, key) == ticket[key]
                    for key in AdmissionSnapshot.__dataclass_fields__), "ticket")
            require(snapshot.input_sha256 == digest(text), "digest")
            require(snapshot.user_tokens <= 32, "admission")
            require(snapshot.current_kv_tokens + snapshot.rendered_incremental_tokens + 128 <= 1024, "admission")
            if self._ledger.revision == 0 and len(text) <= 20:
                require(snapshot.runtime_prefill_tokens <= 128, "prefill")
            child = self._child
            require(child is not None)
            try:
                sample = self._sampler.sample(child_pid=child.pid, child_pgid=child.pgid)
                self._validate_sample(sample)
                profile = self._lock.product_profile
                if self._measurement_grant is not None:
                    self._measurement_grant.check_sample(sample)
                    decision = MemoryDecision.GENERATE
                else:
                    decision = memory_decision(sample,
                        min_mem_available_speak_bytes=profile["min_mem_available_speak_bytes"],
                        min_mem_available_generate_bytes=profile["min_mem_available_generate_bytes"],
                        previous=None)
                self._previous_sample = sample
                if self._observer is not None:
                    self._observer.memory(sample, generation=snapshot.generation,
                                          lifecycle_point="pre_generate")
            except BaseException:
                await self._destroy()
                raise LLMFatalError("MEMORY_SAMPLE_INVALID") from None
            if decision is not MemoryDecision.GENERATE:
                self.mark_recycle_pending(snapshot.session_id, snapshot.generation)
                raise MemoryAdmissionDenied(speak_allowed=decision is MemoryDecision.NOTICE)
            event = await self._request(self._frame("GENERATE", snapshot.session_id,
                snapshot.generation, conversation_revision=self._ledger.revision,
                ticket=snapshot.ticket, text=text, input_sha256=snapshot.input_sha256))
            await self.observe_memory("post_generate")
            if event["event"] == "REQUEST_FAILED":
                if self._observer is not None:
                    self._observer.native_timing(llm_terminal=event["terminal_monotonic_ns"],
                                                 clock_mapped=self._clock_mapped)
                raise ReplaceableGenerationFailure(event["code"])
            result = SemanticGeneration(event["text"], event["end"], tuple(self._ledger.fragments),
                GenerationMetrics(**{key: event[key] for key in GenerationMetrics.__dataclass_fields__}))
            self._ledger.fragments.clear()
            if self._observer is not None:
                self._observer.generated(result.metrics, clock_mapped=self._clock_mapped)
            return result

    async def discard_ticket(self, snapshot: AdmissionSnapshot) -> TicketDiscardProof:
        async with self.serialized():
            self.assert_conversation(snapshot.session_id, snapshot.generation)
            ticket = self._ledger.ticket
            require(ticket is not None and all(type(getattr(snapshot, key)) is type(ticket[key]) and getattr(snapshot, key) == ticket[key]
                    for key in AdmissionSnapshot.__dataclass_fields__), "ticket")
            event = await self._request(self._frame("DISCARD_TICKET", snapshot.session_id,
                snapshot.generation, conversation_revision=self._ledger.revision,
                ticket=snapshot.ticket, input_sha256=snapshot.input_sha256))
            return TicketDiscardProof(**{key: event[key] for key in TicketDiscardProof.__dataclass_fields__})

    async def close_conversation(self, session_id: str, generation: int, reason: str):
        from sbd.core.state_manager.ports import ConversationCloseProof
        async with self.serialized():
            if reason == "replacement":
                reason = "replace_generation_failure" if self._ledger.state == "TAINTED" else "replace_context"
            reason = {"session_rest": "session_end", "session_interrupt": "interrupt",
                      "session_error": "error", "session_shutdown": "shutdown"}.get(reason, reason)
            if self._pending == (session_id, generation) and reason == "session_end":
                reason = "memory_pressure"
            await self._request(self._frame("CLOSE", session_id, generation, reason=reason))
            proof = ConversationCloseProof(session_id, generation, True, True, True)
            self._closed_proof = proof
            await self.observe_memory("post_session_close")
            return proof

    def mark_recycle_pending(self, session_id: str, generation: int) -> None:
        require(self._ledger.claim == (session_id, generation), "identity")
        require(self._pending in {None, (session_id, generation)}, "recovery")
        if self._pending is None:
            self._authorization = None
            self._recovery_ticket = None
        self._pending = (session_id, generation)
        self.state = AdapterState.RECYCLE_PENDING

    async def authorize_recovery(self, session_id: str, generation: int, proof: object) -> None:
        require(self._pending == (session_id, generation), "recovery")
        require(proof == self._closed_proof and proof is not None, "proof")
        require(self._ledger.claim is None and self._ledger.active is None, "proof")
        if self._authorization is None:
            self._authorization = asyncio.create_task(self._authorized_recovery())
        await asyncio.shield(self._authorization)

    async def _authorized_recovery(self) -> None:
        try:
            self._recovery_ticket = self._schedule_recovery((RESOURCE_KEY,))
            require(getattr(self._recovery_ticket, "keys", None) == (RESOURCE_KEY,), "recovery")
            await self._wait_recovery(self._recovery_ticket)
            require(self.state is AdapterState.ENGINE_READY and self._ledger.claim is None, "recovery")
            self._pending = None
        except BaseException:
            await self._destroy()
            raise LLMFatalError("planned recovery failed") from None

    async def abort(self) -> None:
        active = self._ledger.active
        if active is None:
            await self._operation_done.wait()
            return
        child = self._child
        require(child is not None)
        if active["op"] == "DISCARD_TICKET":
            self._atomic_interrupt = True
            await asyncio.shield(self._operation_done.wait())
            return
        if not self._ledger.cancelled:
            frame = {"protocol": 3, "op": "CANCEL", "request_id": active["request_id"]}
            self._ledger.command(frame)
            await child.send(frame)
        await asyncio.shield(self._operation_done.wait())

    async def _destroy(self) -> None:
        self.state = AdapterState.DESTROYED
        from_reader = asyncio.current_task() is self._reader_task
        task = self._destruction_task
        if task is None:
            task = self._destruction_task = asyncio.create_task(self._destroy_owner())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            if not from_reader:
                await asyncio.shield(task)
            raise

    async def _destroy_owner(self) -> None:
        self.state = AdapterState.DESTROYED
        reader = self._reader_task
        if reader is not None and reader is not asyncio.current_task():
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
        self._reader_task = None
        child, self._child = self._child, None
        if child is not None:
            await child.force_terminate()
            self.last_termination_evidence = getattr(child, "termination_evidence", None)
        self._ledger = ProtocolLedger(self._issued_tickets)
        self._ledger.state = "DESTROYED"
        while not self._responses.empty():
            self._responses.get_nowait()
        self._responses.put_nowait(LLMFatalError("LLM owner destroyed"))
        self._operation_done.set()

    async def force_abort(self) -> ForceAbortReport:
        await self._destroy()
        self._responses.put_nowait(LLMFatalError("LLM owner destroyed"))
        return ForceAbortReport((RESOURCE_KEY,))

    async def stop(self) -> None:
        if self.state is AdapterState.STOPPED:
            return
        authorization = self._authorization
        if authorization is not None and not authorization.done():
            authorization.cancel()
            await asyncio.gather(authorization, return_exceptions=True)
        if self._ledger.active is not None:
            await self.abort()
        if self._ledger.claim is not None:
            await self.close_conversation(*self._ledger.claim, "shutdown")
        reader = self._reader_task
        if reader is not None:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
            self._reader_task = None
        child = self._child
        if child is not None:
            await child.stop()
        self._child = None
        self._ledger = ProtocolLedger(self._issued_tickets)
        self._pending = self._closed_proof = self._recovery_ticket = None
        self._authorization = None
        self.state = AdapterState.STOPPED

    async def rebuild(self, bus: object = None, config: object = None) -> None:
        require(self._ledger.claim is None, "recovery")
        if self._child is not None:
            await self.observe_memory("pre_replacement")
        await self._destroy()
        self.state = AdapterState.RECOVERING
        await self._start_replacement()
        await self.observe_memory("post_replacement")
