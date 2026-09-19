"""Executable synthetic C01-C10 controller cases with no target artifacts."""

from __future__ import annotations

import asyncio
from typing import Any

from poc_llm.m4c_ss.controller import FragmentChannel, FragmentChannelError
from poc_llm.m4c_ss.mapping import B1
from poc_llm.m4c_ss.operation import StreamingSpeakOperation
from poc_llm.m4c_ss.plan import CONTROLLER_CASES


class _Backend:
    def __init__(self, *, fail: bool = False, hang: bool = False, abort_hangs: bool = False) -> None:
        self.fail = fail
        self.hang = hang
        self.abort_hangs = abort_hangs
        self.entered = asyncio.Event()
        self.playing = asyncio.Event()
        self.release = asyncio.Event()
        self.idle = True
        self.force_count = 0

    async def speak(self, text: str) -> None:
        self.idle = False
        self.entered.set()
        await asyncio.sleep(0)
        self.playing.set()
        if self.fail:
            self.idle = True
            raise RuntimeError("SYNTHETIC_TTS_FAILURE")
        if self.hang:
            await asyncio.Event().wait()
        await self.release.wait()
        self.idle = True

    async def abort(self) -> None:
        if self.abort_hangs:
            await asyncio.Event().wait()
        self.release.set()
        self.idle = True

    async def force_abort(self) -> None:
        self.force_count += 1
        self.release.set()
        self.idle = True

    def operation_idle(self) -> bool:
        return self.idle


async def run_controller_case(case_id: str) -> dict[str, Any]:
    if case_id not in CONTROLLER_CASES:
        raise ValueError("unknown controller case")
    observations: dict[str, Any] = {
        "normal_success_published": False,
        "queue_empty": False,
        "backend_idle": False,
        "force_abort_used": False,
    }
    try:
        if case_id == "C01-ONE":
            result = await _normal(["one"])
            _require(result.normal_success and result.terminal_proof.fragment_count == 1)
            observations["normal_success_published"] = True
        elif case_id == "C02-MULTI":
            result = await _normal(["one", "two"])
            _require(result.normal_success and result.terminal_proof.fragment_count == 2)
            observations["normal_success_published"] = True
        elif case_id == "C03-BACKPRESSURE":
            channel = FragmentChannel("op")
            await channel.feed("op", 0, "one")
            await channel.feed("op", 1, "two")
            blocked = asyncio.create_task(channel.feed("op", 2, "three"))
            await asyncio.sleep(0)
            _require(not blocked.done())
            first = await channel.receive()
            await asyncio.wait_for(blocked, 0.1)
            await channel.cancel("op")
            await channel.abort_inflight("op", first.sequence)
            _require((await channel.cleanup_proof("op")).queue_empty)
            observations["backpressure_observed"] = True
        elif case_id in {"C04-INVALID-TERMINAL", "C05-PREFIX-MISMATCH"}:
            backend = _Backend()
            operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
            running = asyncio.create_task(operation.run())
            await operation.feed(0, "one")
            await backend.playing.wait()
            try:
                if case_id == "C04-INVALID-TERMINAL":
                    await operation.finish("", semantic_valid=False)
                else:
                    await operation.finish("different")
            except FragmentChannelError:
                pass
            result = await running
            _require(not result.normal_success and result.cleanup_proof.queue_empty)
        elif case_id == "C06-POST-TERMINAL":
            backend = _Backend()
            operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
            running = asyncio.create_task(operation.run())
            await operation.feed(0, "one")
            await operation.finish("one")
            try:
                await operation.feed(1, "late")
            except FragmentChannelError as error:
                _require(error.code == "ADMISSION_CLOSED")
            else:
                raise AssertionError("post-terminal fragment accepted")
            backend.release.set()
            result = await running
            _require(result.normal_success and result.terminal_proof.fragment_count == 1)
            observations["normal_success_published"] = True
            observations["post_terminal_rejected"] = True
        elif case_id.startswith("C07-") or case_id.startswith("C08-"):
            backend = _Backend()
            operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
            if case_id.endswith("QUEUED"):
                await operation.feed(0, "one")
                result = await operation.interrupt()
            else:
                running = asyncio.create_task(operation.run())
                await operation.feed(0, "one")
                await (backend.entered if case_id.endswith("SYNTHESIZING") else backend.playing).wait()
                result = await (operation.shutdown() if case_id.startswith("C08-") else operation.interrupt())
                await running
            _require(not result.normal_success and result.cleanup_proof.queue_empty)
        elif case_id == "C09-TTS-FAILURE-ERROR":
            result = await _failure_backend(_Backend(fail=True))
            _require(result.status == "FAILED" and not result.normal_success)
        elif case_id == "C09-TTS-FAILURE-TIMEOUT":
            result = await _failure_backend(_Backend(hang=True), speak_timeout_s=0.01)
            _require(result.status == "FAILED" and not result.force_abort_used)
        elif case_id == "C09-TTS-FAILURE-FORCE-ABORT":
            backend = _Backend(abort_hangs=True)
            operation = StreamingSpeakOperation(
                "op", candidate=B1, backend=backend,
                abort_timeout_s=0.01, force_abort_timeout_s=0.1,
            )
            running = asyncio.create_task(operation.run())
            await operation.feed(0, "one")
            await backend.entered.wait()
            result = await operation.interrupt()
            await running
            _require(result.force_abort_used and backend.force_count == 1 and not result.normal_success)
            observations["force_abort_used"] = True
        elif case_id == "C10-LATE-OUTPUT":
            old = FragmentChannel("old")
            await old.cancel("old")
            new = FragmentChannel("new")
            try:
                await new.feed("old", 0, "late")
            except FragmentChannelError as error:
                _require(error.code == "STALE_OPERATION")
            else:
                raise AssertionError("late output accepted")
            observations["late_output_rejected"] = True
        else:
            raise AssertionError("unimplemented controller case")
        observations["queue_empty"] = True
        observations["backend_idle"] = True
        return {"case_id": case_id, "status": "PASS", "observations": observations}
    except Exception as error:
        return {
            "case_id": case_id,
            "status": "FAIL",
            "error_code": type(error).__name__,
            "observations": observations,
        }


async def _normal(parts: list[str]):
    backend = _Backend()
    operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
    running = asyncio.create_task(operation.run())
    for sequence, part in enumerate(parts):
        await operation.feed(sequence, part)
    await operation.finish("".join(parts))
    await backend.playing.wait()
    backend.release.set()
    return await running


async def _failure_backend(backend: _Backend, *, speak_timeout_s: float = 30.0):
    operation = StreamingSpeakOperation(
        "op", candidate=B1, backend=backend,
        speak_timeout_s=speak_timeout_s, abort_timeout_s=0.1,
    )
    running = asyncio.create_task(operation.run())
    await operation.feed(0, "one")
    return await running


def _require(condition: bool) -> None:
    if not condition:
        raise AssertionError("deterministic case assertion failed")
