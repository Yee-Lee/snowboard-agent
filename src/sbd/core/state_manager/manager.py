"""Single-inbox State Manager for the M1 runtime contract."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal

from sbd.core.config.models import AppConfig
from sbd.core.event_bus import EventBus, FatalDispatchError, Subscription
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, Event, ExternalMessageArrived,
    LLMResponse, PerceptionResult, ShutdownRequested, State, StateChanged,
    WakeWordDetected, InterruptRequested, new_session_id,
)
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager.convergence import (
    CancelTimeoutPolicy, ConvergenceResult, DefaultSessionConverger,
)
from sbd.core.state_manager.exceptions import (
    ReasonerContractViolation, StateManagerInvariantViolation,
    StateManagerWiringError, WakeListenerControlError, WakeMicReleaseUnprovable,
    WorkerContractViolation,
)
from sbd.core.state_manager.inflight import InFlightRecord
from sbd.core.state_manager.guards import is_allowed_in_state
from sbd.core.state_manager.notices import _RecoveryCompleted, _TaskCompleted, _WakeAckElapsed
from sbd.core.state_manager.ports import (
    ActionPayloadValidator, ExternalMessageControl, RecoveryControl,
    SessionConverger, WakeListenerControl,
)
from sbd.core.state_manager.session import SessionContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _PendingConvergence:
    trigger: Literal["rest", "interrupt", "error", "shutdown"]
    buffer_exit_policy: Literal["flush_to_wake", "discard"]
    recovery_generation: int | None = None


class StateManager:
    """Owns every state transition and in-flight handle on one inbox task."""

    def __init__(
        self,
        config: AppConfig | None = None,
        bus: EventBus | None = None,
        workers: WorkerCatalog | None = None,
        *,
        converger: SessionConverger | None = None,
        recovery: RecoveryControl | None = None,
        action_validator: ActionPayloadValidator | None = None,
        wake_ack_seconds: float | None = None,
        perception_timeouts: dict[str, float] | None = None,
    ) -> None:
        self._bus = bus or EventBus()
        self._workers = workers or WorkerCatalog()
        self._converger = converger or DefaultSessionConverger(timeouts=CancelTimeoutPolicy())
        self._recovery = recovery
        self._action_validator = action_validator
        self._wake_ack_seconds = config.wake.ack_seconds if config else (wake_ack_seconds or 0.3)
        self._perception_timeouts = ({
            "listen": config.perception.timeout_seconds.listen,
            "read": config.perception.timeout_seconds.read,
            "look": config.perception.timeout_seconds.look,
        } if config else (perception_timeouts or {"listen": 10.0, "read": 0.5, "look": 3.0}))
        self._defaults = config.perception.default_perceptions if config else ("listen",)

        self._state: State = "IDLE"
        self._session: SessionContext | None = None
        self._correlation_counter = 0
        self._inbox: asyncio.Queue[Any] = asyncio.Queue()
        self._in_flight: dict[int, InFlightRecord] = {}
        self._subs: list[Subscription] = []
        self._loop_task: asyncio.Task[None] | None = None
        self._wake_timer: asyncio.Task[None] | None = None
        self._recovery_waiter: asyncio.Task[None] | None = None
        self._read_open: tuple[str, int] | None = None
        self._stopped_event = asyncio.Event()
        self._dispatch_ready = asyncio.Event()
        self._loop_should_stop = False
        self._stopping = False
        self._shutting_down = False
        self._pending: _PendingConvergence | None = None
        self._wake_control: WakeListenerControl | None = None
        self._external_control: ExternalMessageControl | None = None
        self._wake_set = False
        self._external_set = False
        self._wake_control_failed = False
        self._wake_control_released = False

    @property
    def state(self) -> State:
        return self._state

    async def wait_stopped(self) -> None:
        await self._stopped_event.wait()
        task = self._loop_task
        if task is None or task.cancelled() or not task.done():
            return
        error = task.exception()
        if error is not None:
            raise error

    def set_wake_listener(self, control: WakeListenerControl | None) -> None:
        if self._wake_set or self._stopping or self._shutting_down:
            raise StateManagerWiringError("WakeListenerControl may only be set once before shutdown")
        self._wake_set = True
        self._wake_control = control

    def set_external_message_control(self, control: ExternalMessageControl) -> None:
        if control is None or self._external_set or self._stopping or self._shutting_down:
            raise StateManagerWiringError("ExternalMessageControl must be set exactly once before shutdown")
        self._external_set = True
        self._external_control = control

    async def start(self) -> None:
        if self._stopping:
            raise StateManagerWiringError("StateManager cannot restart after stop")
        if self._loop_task is not None:
            return
        if self._wake_ack_seconds <= 0 or any(v <= 0 for v in self._perception_timeouts.values()):
            raise StateManagerWiringError("StateManager timing configuration must be positive")
        if not self._defaults or len(set(self._defaults)) != len(self._defaults):
            raise StateManagerWiringError("default perceptions must be non-empty and unique")
        kinds = (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred,
                 ButtonPressed, ExternalMessageArrived, WakeWordDetected,
                 InterruptRequested, ShutdownRequested)
        self._subs = [self._bus.subscribe(kind, self._on_event) for kind in kinds]
        self._loop_task = asyncio.create_task(self._dispatch_loop())
        await self._dispatch_ready.wait()

    async def stop(self) -> None:
        if self._stopping:
            return
        if self._session is not None and not self._shutting_down:
            raise RuntimeError("stop() requires ShutdownRequested and a drained session")
        self._stopping = True
        self._cancel_wake_timer()
        if self._recovery_waiter is not None and not self._recovery_waiter.done():
            self._recovery_waiter.cancel()
            await asyncio.gather(self._recovery_waiter, return_exceptions=True)
        self._recovery_waiter = None
        for sub in self._subs:
            self._bus.unsubscribe(sub)
        self._subs.clear()
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        self._loop_task = None
        self._stopped_event.set()

    async def _on_event(self, event: Event) -> None:
        self._inbox.put_nowait(event)

    async def _dispatch_loop(self) -> None:
        self._dispatch_ready.set()
        try:
            while not self._loop_should_stop:
                item = await self._inbox.get()
                try:
                    await self._handle_item(item)
                    await self._try_progress()
                finally:
                    self._inbox.task_done()
        finally:
            self._stopped_event.set()

    async def _handle_item(self, item: Any) -> None:
        if isinstance(item, _TaskCompleted):
            await self._handle_task_completed(item)
            return
        if isinstance(item, _WakeAckElapsed):
            if self._state == "WAKE" and self._session and item.session_id == self._session.session_id:
                await self._transition("PERCEPTION")
            return
        if isinstance(item, _RecoveryCompleted):
            pending = self._pending
            if (
                pending is None
                or self._state != "ERROR"
                or pending.recovery_generation != item.generation
                or item.waiter is not self._recovery_waiter
            ):
                logger.debug("Dropping stale recovery completion for generation %s", item.generation)
                return
            if item.waiter.cancelled():
                raise asyncio.CancelledError
            error = item.waiter.exception()
            if error is not None:
                raise error
            pending.recovery_generation = None
            self._recovery_waiter = None
            return
        if isinstance(item, (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred, ButtonPressed, ExternalMessageArrived, WakeWordDetected, InterruptRequested, ShutdownRequested)) and not is_allowed_in_state(item, self._state):
            logger.warning("Dropping %s while state is %s", type(item).__name__, self._state)
            return
        if isinstance(item, (PerceptionResult, LLMResponse, ActionCompleted)):
            self._handle_fact(item)
            return
        if isinstance(item, ErrorOccurred):
            if self._state == "ERROR":
                if self._pending is not None:
                    self._pending.buffer_exit_policy = "discard"
                return
            await self._transition("ERROR", trigger="error")
            return
        if isinstance(item, ShutdownRequested):
            await self._begin_shutdown()
            return
        if isinstance(item, InterruptRequested):
            if self._state not in {"IDLE", "ERROR"}:
                await self._begin_convergence("interrupt")
            return
        if isinstance(item, (ButtonPressed, WakeWordDetected, ExternalMessageArrived)):
            if self._shutting_down:
                logger.warning("Dropping %s while state is %s", type(item).__name__, self._state)
                return
            if isinstance(item, ExternalMessageArrived) and self._state != "IDLE":
                if self._external_control is None:
                    raise StateManagerWiringError("External signal received before control late-fill")
                assert self._session is not None
                if self._state != "ERROR" and "read" in self._session.selected_perceptions:
                    await self._external_control.assign_to_turn(
                        item.message_id, self._session.session_id, self._session.turn_id
                    )
                elif self._state != "ERROR":
                    await self._external_control.mark_pending(item.message_id, self._session.session_id)
                else:
                    logger.warning("Dropping external signal while ERROR convergence is active")
                return
            if self._state != "IDLE":
                logger.warning("Dropping %s while state is %s", type(item).__name__, self._state)
                return
            if isinstance(item, ExternalMessageArrived):
                if self._external_control is None:
                    raise StateManagerWiringError("External signal received before control late-fill")
                await self._enter_wake("external_message", item)
            else:
                if isinstance(item, WakeWordDetected) and not self._wake_set:
                    raise StateManagerWiringError("Wake signal received before control late-fill")
                await self._enter_wake("wake_word" if isinstance(item, WakeWordDetected) else "button")

    def _handle_fact(self, fact: PerceptionResult | LLMResponse | ActionCompleted) -> None:
        if self._session is None or fact.session_id != self._session.session_id or fact.turn_id != self._session.turn_id:
            logger.warning("Dropping stale terminal fact")
            return
        record = self._in_flight.get(fact.correlation_id)
        if record is None or record.terminal_fact is not None:
            logger.warning("Dropping unknown or duplicate terminal fact")
            return
        expected = {"perception": PerceptionResult, "think": LLMResponse, "action": ActionCompleted}[record.phase]
        if not isinstance(fact, expected):
            raise WorkerContractViolation(f"{record.kind} published the wrong terminal fact")
        fact_kind = getattr(fact, "kind", None)
        if record.phase != "think" and fact_kind != record.kind:
            raise WorkerContractViolation(
                f"{record.kind} published a terminal fact for kind={fact_kind}"
            )
        record.terminal_fact = fact
        if isinstance(fact, (PerceptionResult, ActionCompleted)) and fact.status in {"error", "timeout"}:
            logger.warning("P5 terminal fact status=%s state=%s kind=%s", fact.status, self._state, fact.kind)
        if isinstance(fact, PerceptionResult):
            self._session.perception_results.append(fact)
        elif isinstance(fact, LLMResponse):
            self._session.llm_response = fact
        else:
            self._session.action_completed = fact

    async def _handle_task_completed(self, notice: _TaskCompleted) -> None:
        record = self._in_flight.get(notice.correlation_id)
        if record is None:
            logger.debug("Dropping stale completion for correlation_id=%s", notice.correlation_id)
            return
        if notice.task is not record.task:
            logger.debug("Dropping completion with mismatched task identity")
            return
        self._in_flight.pop(notice.correlation_id)
        cancelled = notice.task.cancelled()
        if cancelled and record.terminal_fact is None and not record.cancel_requested:
            raise WorkerContractViolation(
                f"Worker {record.kind} was cancelled without convergence request"
            )
        error = None if cancelled else notice.task.exception()
        if error is not None:
            if isinstance(error, FatalDispatchError):
                raise error
            if record.terminal_fact is not None or self._state != "ERROR":
                raise WorkerContractViolation(f"Worker {record.kind} raised after start") from error
            logger.warning("Worker %s exited during convergence: %r", record.kind, error)
        elif not cancelled and record.terminal_fact is None and not record.cancel_requested:
            raise StateManagerInvariantViolation(
                f"Worker {record.kind} returned without publishing a terminal fact"
            )

    async def _transition(self, new_state: State, *, trigger: str | None = None) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        logger.info("State transition %s -> %s", old, new_state)
        await self._bus.publish(StateChanged(old, new_state))
        if new_state == "IDLE":
            await self._enter_idle()
        elif new_state == "PERCEPTION":
            await self._enter_perception()
        elif new_state == "THINK":
            await self._enter_think()
        elif new_state == "ACTION":
            await self._enter_action()
        elif new_state == "ERROR":
            await self._begin_convergence(trigger or "error")

    async def _enter_wake(self, source: Literal["button", "wake_word", "external_message"], message: ExternalMessageArrived | None = None) -> None:
        self._session = SessionContext(session_id=new_session_id(), wake_source=source, turn_id=0)
        if source == "external_message":
            assert self._external_control is not None
            assert message is not None
            await self._external_control.assign_to_session(
                message.message_id, self._session.session_id
            )
            self._session.selected_perceptions = ("read",)
        else:
            await self._suspend_wake()
            self._session.selected_perceptions = ("listen",)
        await self._transition("WAKE")
        async def timer(sid: str) -> None:
            await asyncio.sleep(self._wake_ack_seconds)
            self._inbox.put_nowait(_WakeAckElapsed(sid))
        self._wake_timer = asyncio.create_task(timer(self._session.session_id))

    async def _enter_idle(self) -> None:
        self._cancel_wake_timer()
        await self._close_read()
        self._session = None
        await self._resume_wake()

    async def _suspend_wake(self) -> None:
        if self._wake_control is None or self._wake_control_released:
            return
        try:
            await self._wake_control.suspend()
        except Exception as exc:
            logger.warning("wake suspend failed; requesting release proof: %r", exc)
            try:
                await self._wake_control.ensure_released()
            except Exception as release_error:
                self._wake_control_failed = True
                raise WakeMicReleaseUnprovable("unable to prove wake microphone release") from release_error
        self._wake_control_released = True

    async def _resume_wake(self) -> None:
        if self._wake_control is None or self._wake_control_failed or self._shutting_down:
            return
        try:
            await self._wake_control.resume()
            self._wake_control_released = False
        except Exception:
            self._wake_control_failed = True
            logger.warning("wake resume failed; voice wake disabled", exc_info=True)

    def _cancel_wake_timer(self) -> None:
        if self._wake_timer is not None:
            self._wake_timer.cancel()
            self._wake_timer = None

    def _next_correlation(self) -> int:
        self._correlation_counter += 1
        return self._correlation_counter

    def _start_worker(self, phase: Literal["perception", "think", "action"], kind: str, worker: Any, call: Any) -> None:
        assert self._session is not None
        correlation_id = self._next_correlation()
        task = asyncio.create_task(call(correlation_id))
        self._in_flight[correlation_id] = InFlightRecord(
            correlation_id, self._session.session_id, self._session.turn_id,
            phase, kind, worker, task,
        )
        task.add_done_callback(partial(self._enqueue_completion, kind, correlation_id))

    def _enqueue_completion(self, kind: str, correlation_id: int, task: asyncio.Task[Any]) -> None:
        self._inbox.put_nowait(_TaskCompleted(kind, correlation_id, task))

    async def _enter_perception(self) -> None:
        self._cancel_wake_timer()
        if self._session is None:
            return
        self._session.turn_id += 1
        self._session.perception_results.clear()
        self._session.llm_response = None
        self._session.action_completed = None
        selected = self._session.selected_perceptions or self._defaults
        selected = tuple(dict.fromkeys(
            kind for kind in selected if kind in self._workers.perception_kinds
        ))
        if not selected:
            raise StateManagerInvariantViolation("No registered perception is available")
        self._session.selected_perceptions = selected
        if "read" in selected:
            if self._external_control is None:
                await self._transition("ERROR", trigger="error")
                return
            try:
                await self._external_control.begin_read(
                    self._session.session_id, self._session.turn_id
                )
            except Exception as exc:
                logger.error("Unable to open external-message read window: %s", exc)
                await self._transition("ERROR", trigger="error")
                return
            self._read_open = (self._session.session_id, self._session.turn_id)
        session_id = self._session.session_id
        turn_id = self._session.turn_id
        for kind in selected:
            worker = self._workers.perception(kind)
            self._start_worker("perception", kind, worker,
                lambda cid, w=worker, k=kind: w.perceive(
                    session_id, turn_id, cid, self._perception_timeouts[k]
                ))

    async def _enter_think(self) -> None:
        if self._session is None:
            return
        worker = self._workers.reasoner()
        pending = (
            await self._external_control.pending_ids(self._session.session_id)
            if self._external_control is not None
            else ()
        )
        session_id = self._session.session_id
        turn_id = self._session.turn_id
        results = tuple(self._session.perception_results)
        self._start_worker("think", "reasoner", worker,
            lambda cid: worker.reason(session_id, turn_id, cid, results, pending))

    async def _enter_action(self) -> None:
        if self._session is None or self._session.llm_response is None:
            raise StateManagerInvariantViolation("ACTION entered without LLM response")
        response = self._session.llm_response
        worker = self._workers.action(response.action_kind)
        session_id = self._session.session_id
        turn_id = self._session.turn_id
        self._start_worker("action", response.action_kind, worker,
            lambda cid: worker.execute(session_id, turn_id, cid, response.action_payload))

    async def _validate_response(self, response: LLMResponse) -> None:
        if response.action_kind not in {"speak", "tool", "rest"}:
            raise ReasonerContractViolation("unknown action kind")
        if self._action_validator is not None:
            try:
                await self._action_validator.validate(
                    response.action_kind, response.action_payload
                )
            except Exception as exc:
                raise ReasonerContractViolation("action payload rejected") from exc
        if response.action_kind == "rest":
            return
        assert self._session is not None
        normalized = tuple(dict.fromkeys(
            kind for kind in response.next_perceptions
            if kind in self._workers.perception_kinds
        ))
        if not normalized:
            raise ReasonerContractViolation("no usable next perceptions")
        self._session.next_perceptions = normalized

    async def _close_read(self) -> None:
        if self._read_open is None:
            return
        session_id, turn_id = self._read_open
        self._read_open = None
        if self._external_control is not None:
            await self._external_control.close_read(session_id, turn_id)

    async def _try_progress(self) -> None:
        if self._pending is not None:
            await self._finish_convergence_if_ready()
            return
        if self._in_flight:
            return
        if self._state == "PERCEPTION":
            assert self._session is not None
            if len(self._session.perception_results) == len(self._session.selected_perceptions):
                await self._close_read()
                await self._transition("THINK")
        elif self._state == "THINK":
            if self._session is not None and self._session.llm_response is not None:
                try:
                    await self._validate_response(self._session.llm_response)
                except ReasonerContractViolation as exc:
                    logger.error("Reasoner response rejected: %s", exc)
                    await self._transition("ERROR", trigger="error")
                else:
                    await self._transition("ACTION")
        elif self._state == "ACTION":
            assert self._session is not None
            completed = self._session.action_completed
            if completed is None:
                return
            if completed.kind == "rest":
                await self._begin_convergence("rest")
            else:
                self._session.selected_perceptions = self._session.next_perceptions if completed.status == "ok" else self._defaults
                await self._transition("PERCEPTION")

    async def _begin_convergence(self, trigger: Literal["rest", "interrupt", "error", "shutdown"]) -> None:
        if self._pending is not None:
            if trigger == "shutdown":
                self._pending.trigger = "shutdown"
                self._pending.buffer_exit_policy = "discard"
                self._pending.recovery_generation = None
                if self._recovery_waiter is not None and not self._recovery_waiter.done():
                    self._recovery_waiter.cancel()
            return
        for record in self._in_flight.values():
            record.cancel_requested = True
        result: ConvergenceResult = await self._converger.converge(tuple(self._in_flight.values()), trigger)
        policy: Literal["flush_to_wake", "discard"] = "flush_to_wake" if trigger == "rest" else "discard"
        self._pending = _PendingConvergence(trigger, policy)
        if result.destroyed_backends and trigger != "shutdown":
            if self._recovery is None:
                raise StateManagerInvariantViolation("destroyed backends require RecoveryControl")
            ticket = self._recovery.begin_recovery(result.destroyed_backends)
            self._pending.recovery_generation = ticket.generation

            async def wait_recovery() -> None:
                await self._recovery.wait_recovery(ticket)

            waiter = asyncio.create_task(wait_recovery())
            self._recovery_waiter = waiter
            waiter.add_done_callback(
                lambda done, generation=ticket.generation: self._inbox.put_nowait(
                    _RecoveryCompleted(generation, done)
                )
            )
            if self._state != "ERROR":
                await self._transition("ERROR")
        await self._finish_convergence_if_ready()

    async def _finish_convergence_if_ready(self) -> None:
        pending = self._pending
        if pending is None or self._in_flight or pending.recovery_generation is not None:
            return
        if pending.trigger == "shutdown":
            await self._close_read()
            self._session = None
            self._pending = None
            self._loop_should_stop = True
            return
        await self._close_read()
        if pending.buffer_exit_policy == "discard" and self._external_control is not None:
            await self._external_control.discard_pending()
        self._pending = None
        await self._transition("IDLE")
        if pending.buffer_exit_policy == "flush_to_wake" and self._external_control is not None:
            await self._external_control.flush_to_wake()

    async def _begin_shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._cancel_wake_timer()
        if self._external_control is not None:
            await self._external_control.discard_pending()
        if self._recovery is not None:
            await self._recovery.prepare_shutdown()
        await self._begin_convergence("shutdown")
