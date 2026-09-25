#!/usr/bin/env python3
"""Instrumented exact-product application child for M4C-PI-S05."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sbd.core.display import DisplayArbiter
from sbd.core.display.lifecycle import DisplayLifecycle
from sbd.core.events import ShutdownRequested
from sbd.core.resource_manager import ResourceManager
from sbd.core.state_manager import StateManager
import sbd.main as app_main


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


async def _run(
    config_path: Path, observation_path: Path, ready_path: Path
) -> int:
    # The coordinator's SBD_M4C_* variables belong to pytest, not to the
    # product configuration namespace.  The exact-product child receives its
    # config only through the explicit path above.
    for key in tuple(os.environ):
        if key.startswith("SBD_M4C_"):
            os.environ.pop(key)

    observation: dict[str, Any] = {
        "schema_version": 1,
        "variant": "APP_EXIT",
        "shutdown_signal_count": 0,
        "wake_entry_count": 0,
        "shutdown_blank_seen": False,
        "blank_before_display_close": False,
        "stop_failure_count": -1,
    }

    original_shutdown = DisplayLifecycle.begin_shutdown
    original_display_stop = DisplayArbiter.stop
    original_stop_all = ResourceManager.stop_all
    original_enter_wake = StateManager._enter_wake
    original_handle_item = StateManager._handle_item
    original_log_info = app_main.logger.info

    def observed_shutdown(self: DisplayLifecycle) -> bool:
        accepted = original_shutdown(self)
        snapshot = self._arbiter.snapshot()
        observation["shutdown_blank_seen"] = bool(
            accepted
            and snapshot.fullscreen is not None
            and snapshot.fullscreen.template == "fullscreen.blank"
        )
        return accepted

    async def observed_display_stop(self: DisplayArbiter) -> None:
        snapshot = self.snapshot()
        observation["blank_before_display_close"] = bool(
            observation["shutdown_blank_seen"]
            and snapshot.fullscreen is not None
            and snapshot.fullscreen.template == "fullscreen.blank"
        )
        await original_display_stop(self)

    async def observed_stop_all(self: ResourceManager):
        report = await original_stop_all(self)
        observation["stop_failure_count"] = len(report.failures)
        return report

    async def observed_enter_wake(self: StateManager, *args, **kwargs) -> None:
        observation["wake_entry_count"] += 1
        await original_enter_wake(self, *args, **kwargs)

    async def observed_handle_item(self: StateManager, event: object) -> None:
        if isinstance(event, ShutdownRequested):
            observation["shutdown_signal_count"] += 1
        await original_handle_item(self, event)

    def observed_log_info(message: object, *args, **kwargs) -> None:
        original_log_info(message, *args, **kwargs)
        if message == "M2 runtime ready state=IDLE":
            ready_path.write_text("READY\n", encoding="ascii")
            os.chmod(ready_path, 0o600)

    DisplayLifecycle.begin_shutdown = observed_shutdown
    DisplayArbiter.stop = observed_display_stop
    ResourceManager.stop_all = observed_stop_all
    StateManager._enter_wake = observed_enter_wake
    StateManager._handle_item = observed_handle_item
    app_main.logger.info = observed_log_info
    try:
        exit_code = await app_main.run_app(str(config_path))
        observation["application_exit_code"] = exit_code
        return exit_code
    finally:
        app_main.logger.info = original_log_info
        _write_json(observation_path, observation)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(asyncio.run(_run(args.config, args.observation, args.ready)))


if __name__ == "__main__":
    main()
