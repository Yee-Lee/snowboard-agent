"""Parent-side owner for the isolated M4b LiteRT-LM child."""

from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import signal
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Protocol

from sbd.adaptor.errors import AdapterRejected, AdapterTimeout
from sbd.cognition.litert_lm.lock import LLMArtifactLock, LLMLockError
from sbd.cognition.llm import (
    LLMGeneration,
    LLMResourceSample,
    LLMResourceSampler,
    ScheduleRecovery,
    WaitRecovery,
)
from sbd.cognition.llm_child_protocol import (
    MAX_CONTROL_BYTES,
    PROTOCOL_VERSION,
    LLMProtocolError,
    LLMWireCancelled,
    LLMWireError,
    LLMWireResult,
    encode_cancel,
    encode_frame,
    encode_generate,
    parse_ready,
    parse_terminal,
    read_frame,
)
from sbd.cognition.prompt_builder import ReasoningInput
from sbd.core.config.models import LLMConfig
from sbd.core.lifecycle import ForceAbortReport


RESOURCE_KEY = "backend.cognition.reasoner.llm"


class LLMFatalError(RuntimeError):
    """A sanitized non-P5 child ownership or protocol failure."""


@dataclass(frozen=True, slots=True)
class LLMStartupEvidence:
    engine_load_latency_ms: float
    prewarm_latency_ms: float
    ready_latency_ms: float
    prewarm_prompt_sha256: str


@dataclass(frozen=True, slots=True)
class LLMCancelEvidence:
    native_cancel_calls: int
    worker_joined: bool


@dataclass(frozen=True, slots=True)
class LLMTerminationEvidence:
    term_sent: bool
    kill_sent: bool
    waitpid_exit_code: int
    orphan_count: int


def _load_startup_evidence(path: Path, *, ready_latency_ms: float) -> LLMStartupEvidence:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LLMFatalError("child startup evidence is unavailable") from error
    if type(raw) is not dict or set(raw) != {
        "schema_version", "engine_load_latency_ms", "prewarm_latency_ms",
        "prewarm_prompt_sha256",
    }:
        raise LLMFatalError("child startup evidence shape is invalid")
    engine_load = raw["engine_load_latency_ms"]
    prewarm = raw["prewarm_latency_ms"]
    expected_prompt = "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d"
    if (
        raw["schema_version"] != 1
        or type(engine_load) not in (int, float)
        or type(prewarm) not in (int, float)
        or not math.isfinite(engine_load)
        or not math.isfinite(prewarm)
        or engine_load < 0
        or prewarm < 0
        or type(ready_latency_ms) not in (int, float)
        or not math.isfinite(ready_latency_ms)
        or ready_latency_ms < 0
        or raw["prewarm_prompt_sha256"] != expected_prompt
    ):
        raise LLMFatalError("child startup evidence identity is invalid")
    return LLMStartupEvidence(
        float(engine_load), float(prewarm), float(ready_latency_ms), expected_prompt,
    )


class AdapterState(Enum):
    STOPPED = auto()
    AUTHENTICATING = auto()
    STARTING = auto()
    ENGINE_LOADED = auto()
    PREWARMING = auto()
    READY = auto()
    GENERATING = auto()
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

    def __init__(self, cfg: LLMConfig, lock: LLMArtifactLock, generation: int) -> None:
        self._cfg = cfg
        self._lock = lock
        self._generation = generation
        self._process: asyncio.subprocess.Process | None = None
        self._workdir: Path | None = None
        self.pid = 0
        self.pgid = 0
        self.startup_evidence: LLMStartupEvidence | None = None
        self.termination_evidence: LLMTerminationEvidence | None = None

    async def start(self) -> Mapping[str, object]:
        assert self._cfg.runtime_python is not None
        assert self._cfg.model_path is not None
        assert self._cfg.product_config_path is not None
        runtime_root = self._cfg.runtime_python.parent.parent / "lib/python3.13/site-packages"
        worker_path = Path(__file__).with_name("worker.py").resolve()
        self._workdir = Path(tempfile.mkdtemp(prefix="m4b-llm-"))
        startup_evidence_path = self._workdir / "startup-evidence.json"
        argv = [
            str(self._cfg.runtime_python), "-I", "-B", str(worker_path),
            "--model", str(self._cfg.model_path),
            "--product-config", str(self._cfg.product_config_path),
            "--runtime-root", str(runtime_root),
            "--candidate-id", self._lock.identity.candidate_id,
            "--pairing-revision", self._lock.identity.pairing_revision,
            "--platform", self._lock.identity.platform,
            "--runtime-sha256", self._lock.identity.runtime_sha256,
            "--native-sha256", str(self._lock.runtime["native_sha256"]),
            "--model-sha256", self._lock.identity.model_sha256,
            "--config-sha256", self._lock.identity.config_sha256,
            "--startup-evidence", str(startup_evidence_path),
        ]
        try:
            started = time.monotonic()
            self._process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=self._workdir,
                env=isolated_child_environment(runtime_root),
                start_new_session=True,
                limit=MAX_CONTROL_BYTES + 1,
            )
            self.pid = self._process.pid
            self.pgid = self.pid
            assert self._process.stdout is not None
            ready = await asyncio.wait_for(
                read_frame(self._process.stdout), self._cfg.child_ready_timeout_seconds
            )
            self.startup_evidence = _load_startup_evidence(
                startup_evidence_path,
                ready_latency_ms=(time.monotonic() - started) * 1000.0,
            )
            startup_evidence_path.unlink()
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
            raise LLMFatalError("child input closed") from error

    async def receive(self) -> Mapping[str, object]:
        if self._process is None or self._process.stdout is None:
            raise LLMFatalError("child output is unavailable")
        return await read_frame(self._process.stdout)

    async def stop(self) -> None:
        process = self._process
        if process is None:
            await self._cleanup()
            return
        try:
            await self.send({"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION})
            frame = await asyncio.wait_for(self.receive(), self._cfg.child_terminate_timeout_seconds)
            if frame != {"type": "SHUTDOWN_ACK", "protocol_version": PROTOCOL_VERSION}:
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
                    raise LLMFatalError("child process-group exit could not be proven") from error
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
            return {pgid}
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
                raise LLMFatalError("child work-directory cleanup failed") from error
            if workdir.exists() or workdir.is_symlink():
                raise LLMFatalError("child work-directory cleanup failed")
            self._workdir = None


ChildFactory = Callable[[LLMConfig, LLMArtifactLock, int], LLMChild]


class LiteRTLMAdapter:
    def __init__(
        self,
        cfg: LLMConfig,
        *,
        lock: LLMArtifactLock,
        schedule_recovery: ScheduleRecovery,
        wait_recovery: WaitRecovery,
        resource_sampler: LLMResourceSampler,
        child_factory: ChildFactory = SubprocessLLMChild,
    ) -> None:
        self._cfg = cfg
        self._lock = lock
        self._schedule_recovery = schedule_recovery
        self._wait_recovery = wait_recovery
        self._sampler = resource_sampler
        self._child_factory = child_factory
        self._child: LLMChild | None = None
        self._generation = 0
        self._request_counter = 0
        self._attempts = 0
        self._baseline: LLMResourceSample | None = None
        self._ticket: Any = None
        self._active_request_id: str | None = None
        self._terminal_task: asyncio.Task[Mapping[str, object]] | None = None
        self._convergence_event: asyncio.Event | None = None
        self._cancel_sent = False
        self._operation_lock = asyncio.Lock()
        self.state = AdapterState.STOPPED
        self.state_trace: list[AdapterState] = [AdapterState.STOPPED]
        self.startup_evidence: LLMStartupEvidence | None = None
        self.last_cancel_evidence: LLMCancelEvidence | None = None
        self.last_termination_evidence: LLMTerminationEvidence | None = None

    def _set_state(self, state: AdapterState) -> None:
        self.state = state
        self.state_trace.append(state)

    async def start(self) -> None:
        if self.state is AdapterState.READY:
            return
        if self.state is not AdapterState.STOPPED:
            raise LLMFatalError("start requires STOPPED")
        await self._start_replacement()

    async def _start_replacement(self) -> None:
        self._set_state(AdapterState.AUTHENTICATING)
        self._generation += 1
        closure = self._lock.runtime_closure
        if closure is not None:
            runtime_python = self._cfg.runtime_python
            if runtime_python is None:
                self._set_state(AdapterState.STOPPED)
                raise LLMFatalError("LLM product authentication failed")
            runtime_root = runtime_python.parent.parent / "lib/python3.13/site-packages"
            try:
                closure.verify_install(runtime_root)
                self._lock.verify_config_paths(self._cfg)
            except (LLMLockError, OSError) as error:
                self._set_state(AdapterState.STOPPED)
                raise LLMFatalError("LLM product authentication failed") from error
        child = self._child_factory(self._cfg, self._lock, self._generation)
        self._set_state(AdapterState.STARTING)
        try:
            ready = await child.start()
            self._set_state(AdapterState.ENGINE_LOADED)
            self._set_state(AdapterState.PREWARMING)
            parse_ready(ready, expected_identity=self._lock.identity)
            baseline = self._sample(child)
        except asyncio.CancelledError:
            try:
                await child.force_terminate()
            except BaseException as cleanup:
                self._set_state(AdapterState.STOPPED)
                raise LLMFatalError("LLM child startup cancellation cleanup failed") from cleanup
            self._set_state(AdapterState.STOPPED)
            raise
        except BaseException as error:
            cleanup_error: BaseException | None = None
            try:
                await child.force_terminate()
            except BaseException as cleanup:
                cleanup_error = cleanup
            finally:
                self._set_state(AdapterState.STOPPED)
            raise LLMFatalError("LLM child startup failed") from (cleanup_error or error)
        self._child = child
        self.startup_evidence = getattr(child, "startup_evidence", None)
        self._baseline = baseline
        self._attempts = 0
        self._request_counter = 0
        self._ticket = None
        self._set_state(AdapterState.READY)

    def _sample(self, child: LLMChild) -> LLMResourceSample:
        sample = self._sampler.sample(child_pid=child.pid, child_pgid=child.pgid)
        if (
            type(sample.owner_pss_bytes) is not int
            or type(sample.mem_available_bytes) is not int
            or sample.owner_pss_bytes < 0
            or sample.mem_available_bytes < 0
        ):
            raise LLMFatalError("resource sample is invalid")
        return sample

    async def generate(self, value: ReasoningInput) -> LLMGeneration:
        if self._ticket is not None:
            await self._wait_recovery(self._ticket)
        if self._operation_lock.locked():
            raise AdapterRejected("BUSY")
        if self.state is not AdapterState.READY:
            raise LLMFatalError("generation requires READY")
        async with self._operation_lock:
            child = self._child
            if child is None:
                raise LLMFatalError("child owner is absent")
            self._request_counter += 1
            request_id = f"llm.{self._generation}.{self._request_counter}"
            frame = encode_generate(request_id, value)
            self._active_request_id = request_id
            self._cancel_sent = False
            self._convergence_event = asyncio.Event()
            self.state = AdapterState.GENERATING
            try:
                await child.send(frame)
            except BaseException as error:
                await self._destroy(child)
                raise LLMFatalError("child generation write failed") from error
            self._attempts += 1
            self._terminal_task = asyncio.create_task(child.receive())
            deadline_expired = False
            try:
                try:
                    raw = await asyncio.wait_for(
                        asyncio.shield(self._terminal_task),
                        self._cfg.generation_timeout_seconds,
                    )
                except TimeoutError:
                    deadline_expired = True
                    if not self._cancel_sent:
                        self._cancel_sent = True
                        try:
                            await child.send(encode_cancel(request_id))
                        except BaseException as error:
                            await self._destroy(child)
                            raise LLMFatalError("child cancellation write failed") from error
                    raw = await asyncio.wait_for(
                        asyncio.shield(self._terminal_task),
                        self._cfg.terminal_grace_seconds,
                    )
                terminal = parse_terminal(raw, active_request_id=request_id)
            except TimeoutError as error:
                await self._destroy(child)
                raise LLMFatalError("child terminal grace exceeded") from error
            except LLMProtocolError as error:
                await self._destroy(child)
                raise LLMFatalError("child terminal protocol failure") from error
            finally:
                self._active_request_id = None
                self._terminal_task = None
            if isinstance(terminal, LLMWireResult):
                self.state = AdapterState.READY
                generation = LLMGeneration(terminal.response, terminal.metrics)
                await self._after_terminal(child)
                if deadline_expired:
                    raise AdapterTimeout("generation exceeded its deadline")
                return generation
            if isinstance(terminal, LLMWireCancelled):
                self.state = AdapterState.READY
                self.last_cancel_evidence = LLMCancelEvidence(1, True)
                await self._after_terminal(child)
                raise AdapterTimeout("generation cancelled")
            assert isinstance(terminal, LLMWireError)
            if terminal.state != "READY" or terminal.code == "BUSY":
                await self._destroy(child)
                raise LLMFatalError("child reported fatal generation state")
            self.state = AdapterState.READY
            await self._after_terminal(child)
            if terminal.code == "TIMEOUT":
                raise AdapterTimeout("generation timed out")
            raise AdapterRejected("generation rejected")

    async def _after_terminal(self, child: LLMChild) -> None:
        try:
            current = self._sample(child)
        except BaseException as error:
            await self._destroy(child)
            raise LLMFatalError("terminal resource cleanup could not be proven") from error
        assert self._baseline is not None
        recycle = (
            self._attempts >= self._cfg.recycle_max_inference_attempts
            or current.owner_pss_bytes - self._baseline.owner_pss_bytes
            >= self._cfg.recycle_owner_pss_delta_mib * 1024**2
            or current.mem_available_bytes
            < self._cfg.recycle_min_mem_available_mib * 1024**2
        )
        if recycle:
            self.state = AdapterState.RECYCLE_PENDING
            try:
                self._ticket = self._schedule_recovery((RESOURCE_KEY,))
            except BaseException as error:
                await self._destroy(child)
                raise LLMFatalError("planned recovery could not be scheduled") from error
        self._mark_converged()

    def _mark_converged(self) -> None:
        event = self._convergence_event
        if event is not None:
            event.set()

    async def _destroy(self, child: LLMChild) -> None:
        task = self._terminal_task
        if task is not None and not task.done():
            task.cancel()
        try:
            await child.force_terminate()
        finally:
            if task is not None:
                await asyncio.gather(task, return_exceptions=True)
            if self._child is child:
                self._child = None
            self.state = AdapterState.DESTROYED
            self._mark_converged()

    async def abort(self) -> None:
        child = self._child
        request_id = self._active_request_id
        terminal_task = self._terminal_task
        convergence = self._convergence_event
        if convergence is None or convergence.is_set():
            return
        if (
            child is not None
            and request_id is not None
            and terminal_task is not None
            and not self._cancel_sent
        ):
            self._cancel_sent = True
            try:
                await child.send(encode_cancel(request_id))
            except BaseException as error:
                await self._destroy(child)
                raise LLMFatalError("child cancellation write failed") from error
        await asyncio.shield(convergence.wait())

    async def force_abort(self) -> ForceAbortReport:
        child = self._child
        if child is not None:
            await self._destroy(child)
            self.last_termination_evidence = getattr(child, "termination_evidence", None)
        else:
            self.state = AdapterState.DESTROYED
            self._mark_converged()
        return ForceAbortReport((RESOURCE_KEY,))

    async def stop(self) -> None:
        if self.state is AdapterState.STOPPED:
            return
        if self._active_request_id is not None:
            await self.abort()
        child = self._child
        if child is not None:
            await child.stop()
        self._child = None
        self.state = AdapterState.STOPPED

    async def rebuild(self, bus: object = None, config: object = None) -> None:
        self.state = AdapterState.RECOVERING
        old = self._child
        if old is not None:
            try:
                await old.stop()
            except asyncio.CancelledError:
                try:
                    await old.force_terminate()
                except BaseException as cleanup:
                    self._child = None
                    self.state = AdapterState.STOPPED
                    raise LLMFatalError("old child cancellation cleanup failed") from cleanup
                self._child = None
                self.state = AdapterState.STOPPED
                raise
            except BaseException:
                await old.force_terminate()
        self._child = None
        await asyncio.wait_for(self._start_replacement(), self._cfg.rebuild_ready_timeout_seconds)


__all__ = [
    "AdapterState",
    "LLMChild",
    "LLMFatalError",
    "LLMCancelEvidence",
    "LLMStartupEvidence",
    "LLMTerminationEvidence",
    "LiteRTLMAdapter",
    "SubprocessLLMChild",
    "isolated_child_environment",
    "_load_startup_evidence",
]
