#!/usr/bin/env python3
"""Native interrupted-Session/restart regression; not the old Quality catalog.

Fixed new PCM enters the production ASR seam. LLM/TTS/Audio and GPIO callback
handling remain native. Full private observations are retained, without digests.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts import alpha_product as driver
from scripts.alpha_oracle import require

PLAN = [[("INTERRUPTED", "FX-MULTI-FRAGMENT", "KEEP_NEXT")],
        [("AFTER_INTERRUPT", "FX-SHORT-A", "KEEP_NEXT")]]
TEXTS = {"FX-MULTI-FRAGMENT": "請列出三個露營準備重點。",
         "FX-SHORT-A": "請說一句鼓勵的話。"}


class NativeProbe(driver.ProductProbe):
    phase = "provisional"

    async def until(self, predicate):
        await asyncio.wait_for(super().until(predicate), 90)

    def target_active(self):
        from sbd.adaptor.framed_child import ChildState
        control = self.composition._speak_worker._streaming
        if control is None or not control.admitted_count:
            return False
        if self.phase == "provisional":
            tts = self.rm._records["backend.action.speak.tts"].instance
            return self.sm.state == "THINK" and tts.state is ChildState.BUSY
        audio = self.rm._records["core.audio.output"].instance.raw_output
        return (self.sm.state == "ACTION" and control._task is not None
                and not control._task.done() and control._pcm is not None
                and audio._first_write_observed)

    async def stimulate(self):
        from sbd.adaptor.framed_child import ChildState
        self.closing_quality_context = True  # Pause capture when no next PCM is scheduled.
        checks = {}
        self.result["native_checks"] = checks
        try:
            self.result["initial"] = self.idle_snapshot()
            self.initial_pids = self.backend_pids()
            self.first_child = self.rm._records["backend.cognition.reasoner.llm"].instance._child
            self.pending.extend(self.plan[0])
            await self.button()
            await self.until(self.target_active)
            checks["target_phase_active"] = self.target_active()
            first_session = self.sm._session.session_id
            first_control = self.composition._speak_worker._streaming
            await self.button()
            await self.until(lambda: self.sm.state == "IDLE" and self.sm._session is None)
            await self.sm._inbox.join()
            first = self.barrier(first_session)
            self.sessions.append(first)
            checks["interrupted_barrier_clean"] = (
                first["conversation_absent"] and first["main_empty"] and first["display_idle"]
                and first["close_count"] == 1 and first["session_tasks"] == 0
                and first["streaming_controls"] == 0 and first["inflight"] == 0
                and first_control.queue_depth == 0 and not first_control._inflight
                and first_control._pcm is None and first_control._task.done())
            checks["tts_ready_before_restart"] = (
                self.rm._records["backend.action.speak.tts"].instance.state is ChildState.READY)
            checks["recovery_ready_before_restart"] = self.rm.recovery_ready()
            require(all(checks.values()), "INTERRUPTED_BARRIER_FAILED")

            previous_count = len(self.rows)
            self.pending.extend(self.plan[1])
            await self.button()
            await self.until(lambda: len(self.rows) > previous_count)
            second = self.rows[previous_count]
            checks["new_session"] = second["session_id"] != first_session
            await self.until(lambda: any(a["kind"] == "speak" and a["status"] == "ok"
                                        for a in second["actions"]))
            checks["normal_response_after_interrupt"] = (
                len(second["asr"]) == 1 and second["asr"][0]["status"] == "ok"
                and len(second["responses"]) == 1
                and second["responses"][0]["route"] == "KEEP_NEXT"
                and any(v.get("admission_result") == "GENERATE" for v in second["runtime"]))
            await self.until(lambda: self.sm.state == "PERCEPTION")
            await self.button()
            await self.until(lambda: self.sm.state == "IDLE" and self.sm._session is None)
            await self.sm._inbox.join()
            second_barrier = self.barrier(second["session_id"])
            self.sessions.append(second_barrier)
            checks["second_session_closed"] = (
                second_barrier["conversation_absent"] and second_barrier["display_idle"]
                and second_barrier["streaming_controls"] == 0 and second_barrier["inflight"] == 0)
            checks["no_product_fault"] = not self.errors
            require(all(checks.values()), "POST_INTERRUPT_SESSION_FAILED")
            self.result["driver_complete"] = True
        except Exception:
            self.result["failure_code"] = "NATIVE_INTERRUPT_REGRESSION_FAILED"
        finally:
            await self.button(shutdown=True)


async def run(args):
    from sbd.core.resource_manager import ResourceManager
    original_stop = ResourceManager.stop_all
    stops = []

    async def observed_stop(manager):
        report = await original_stop(manager)
        stops.append(len(report.failures))
        return report

    NativeProbe.phase = args.phase
    observation = args.output / "observation.json"
    launch_args = SimpleNamespace(run="quality", config=args.config, fixtures=args.fixtures,
                                 observation=observation, process_start_ns=time.monotonic_ns())
    with patch.object(driver, "session_plan", lambda run: PLAN), \
         patch.object(driver, "ProductProbe", NativeProbe), \
         patch.object(ResourceManager, "stop_all", observed_stop):
        code = await driver.launch(launch_args)
    value = json.loads(observation.read_text())
    report = {"phase": args.phase, "app_exit_code": code,
              "driver_complete": value.get("driver_complete", False),
              "checks": value.get("native_checks", {}),
              "shutdown_failures": sum(stops),
              "cleanup": {k: v for k, v in value["cleanup"].items() if k != "app_absent"}}
    report["pass"] = (code == 0 and report["driver_complete"] and all(report["checks"].values())
                      and bool(stops) and not report["shutdown_failures"]
                      and all(report["cleanup"].values()))
    driver.private_json(args.output / "result.json", report)
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["pass"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prepare-fixtures", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--phase", choices=("provisional", "playback"), default="provisional")
    args = parser.parse_args()
    os.umask(0o077)
    if args.prepare_fixtures:
        with patch.dict(driver.FIXTURE_TEXT, TEXTS, clear=True):
            asyncio.run(driver.prepare_fixtures(args.config, args.prepare_fixtures))
        return 0
    if args.fixtures is None or args.output is None:
        parser.error("--fixtures and --output are required for the native run")
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
