"""Tests for M2-REG-001 scaffold and pure-software platform boundary."""

from __future__ import annotations

import asyncio
import json
import sys

import sbd

from tests.fakes.m2 import (
    AsyncBarrier,
    CallLog,
    MessageFixture,
    MockAppFixture,
    MockHalFixture,
    MockWorkerFixture,
)


def test_m2_reg_001_fixture_barrier_and_call_log(
    fx_barrier_worker: AsyncBarrier,
    fx_call_log: CallLog,
) -> None:
    """M2-REG-001: race fixtures use an explicit barrier, never a sleep."""

    async def exercise_barrier() -> None:
        task = asyncio.create_task(fx_barrier_worker.pause("fact-published"))
        point = await fx_barrier_worker.wait_until_arrived()
        assert point == "fact-published"
        assert not task.done()
        fx_barrier_worker.release()
        await task
        assert task.done()

    asyncio.run(exercise_barrier())
    fx_call_log.record("fact")
    fx_call_log.record("task-done")
    fx_call_log.assert_before("fact", "task-done")
    assert fx_call_log.names() == ("fact", "task-done")


def test_m2_reg_001_fixture_payloads_are_deterministic(
    fx_mock_hal: MockHalFixture,
    fx_mock_worker: MockWorkerFixture,
    fx_message: MessageFixture,
    fx_mock_app: MockAppFixture,
) -> None:
    """M2-REG-001: common M2 fixtures have stable, valid seed data."""
    expected_pcm_bytes = 160 * fx_mock_hal.channels * fx_mock_hal.sample_width_bytes
    assert len(fx_mock_hal.pcm_frame) == expected_pcm_bytes
    assert len(fx_mock_hal.blank_rgb) == (
        fx_mock_hal.image_width * fx_mock_hal.image_height * 3
    )
    assert json.loads(fx_mock_worker.llm_speak_json)["kind"] == "speak"
    assert json.loads(fx_mock_worker.llm_rest_json)["payload"] == {}
    assert fx_message.texts == ("first message", "second message")
    assert fx_mock_app.state_path[0] == fx_mock_app.state_path[-1] == "IDLE"


def test_m2_reg_001_default_import_avoids_pi_dependencies() -> None:
    """M2-REG-001: importing the default package performs no Pi-only import."""
    assert sbd.__name__ == "sbd"
    forbidden_modules = {
        "sounddevice",
        "picamera2",
        "gpiod",
        "LiteRT_LM",
        "litert_lm",
    }
    imported_roots = {name.split(".", 1)[0] for name in sys.modules}
    assert forbidden_modules.isdisjoint(imported_roots)
