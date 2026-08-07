"""Main entrypoint and first-root process supervisor for Snowboard."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from collections.abc import Callable
from pathlib import Path

from sbd.core.config import AppConfig, ConfigError, load_config
from sbd.core.error_observer import ErrorLoggingObserver
from sbd.core.event_bus import EventBus
from sbd.core.events import ShutdownRequested
from sbd.core.logger import (
    bootstrap_logging,
    configure_logging,
    get_logger,
)
from sbd.core.resource_manager import ResourceManager
from sbd.core.state_manager import StateManager
from sbd.core.state_manager.convergence import (
    CancelTimeoutPolicy,
    DefaultSessionConverger,
)

logger = get_logger("main")
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 2
EXIT_STARTUP_ERROR = 3
EXIT_RUNTIME_FATAL = 4

Composition = Callable[[ResourceManager, EventBus, AppConfig], None]


async def run_app(
    config_path: str | None = None,
    *,
    composition: Composition | None = None,
) -> int:
    """Run until normal shutdown or the first supervised fatal condition."""
    try:
        config = load_config(
            local_path=Path(config_path) if config_path else Path("config.local.yaml")
        )
    except ConfigError as error:
        sys.stderr.write(f"Config fatal error: {error}\n")
        return EXIT_CONFIG_ERROR
    except Exception as error:
        sys.stderr.write(f"Config load error: {error}\n")
        return EXIT_CONFIG_ERROR

    logging_runtime = configure_logging(config.log)
    if composition is None:
        from sbd.core.m2_composition import M2Composition

        m2_composition = M2Composition()
        effective_composition: Composition = m2_composition
        action_validator = m2_composition.action_validator
    else:
        effective_composition = composition
        action_validator = None

    loop = asyncio.get_running_loop()
    observer: ErrorLoggingObserver | None = None
    rm: ResourceManager | None = None
    sm: StateManager | None = None
    fatal_bus_task: asyncio.Task[None] | None = None
    stopped_task: asyncio.Task[None] | None = None
    signal_installed: list[signal.Signals] = []
    shutdown_enqueued = False
    exit_code = EXIT_RUNTIME_FATAL

    try:
        bus = EventBus()
        # Arm fatal supervision before any observer/resource can become READY.
        fatal_bus_task = asyncio.create_task(bus.wait_fatal())
        observer = ErrorLoggingObserver(bus)
        await observer.start()

        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(
                abort_default_seconds=config.cancel.abort_timeout_seconds.default,
                force_abort_default_seconds=config.cancel.force_abort_timeout_seconds.default,
                abort_by_kind=config.cancel.abort_timeout_seconds.by_kind,
                force_abort_by_kind=config.cancel.force_abort_timeout_seconds.by_kind,
            )
        )
        rm = ResourceManager(config, bus)
        sm = StateManager(
            config,
            bus,
            rm.catalog,
            converger=converger,
            recovery=rm,
            action_validator=action_validator,
        )
        rm.set_state_manager(sm)
        effective_composition(rm, bus, config)

        try:
            # SM is ready before RM reaches producers; its catalog is filled
            # and sealed by RM before those producers may arm.
            await sm.start()
            stopped_task = asyncio.create_task(sm.wait_stopped())
            await rm.start()
        except Exception as error:
            logger.critical("Startup failed: %s", error, exc_info=True)
            exit_code = EXIT_STARTUP_ERROR
            return exit_code

        def request_shutdown() -> None:
            nonlocal shutdown_enqueued
            if shutdown_enqueued:
                return
            shutdown_enqueued = True
            asyncio.create_task(bus.publish(ShutdownRequested()))

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, request_shutdown)
                signal_installed.append(sig)
            except (NotImplementedError, RuntimeError):
                pass
        logger.info("M1 runtime ready")
        logger.info("M2 runtime ready state=IDLE")

        supervised: set[asyncio.Task[object]] = {
            fatal_bus_task,
            stopped_task,
        }
        done, _ = await asyncio.wait(
            supervised,
            return_when=asyncio.FIRST_COMPLETED,
        )

        root_error: BaseException | None = None
        # A latched Bus fatal is authoritative even if its publisher task also
        # caused another supervised task to complete in the same loop turn.
        if fatal_bus_task in done:
            root_error = fatal_bus_task.exception()
        if root_error is None and stopped_task in done:
            root_error = stopped_task.exception()

        if root_error is not None:
            logger.critical(
                "Runtime fatal error: %s",
                root_error,
                exc_info=(
                    type(root_error),
                    root_error,
                    root_error.__traceback__,
                ),
            )
            exit_code = EXIT_RUNTIME_FATAL
        else:
            exit_code = EXIT_SUCCESS
        return exit_code
    except Exception as error:
        logger.critical("Unhandled runtime fatal: %s", error, exc_info=True)
        exit_code = EXIT_RUNTIME_FATAL
        return exit_code
    finally:
        for sig in signal_installed:
            loop.remove_signal_handler(sig)

        for waiter in (fatal_bus_task, stopped_task):
            if waiter is not None and not waiter.done():
                waiter.cancel()
        await asyncio.gather(
            *(waiter for waiter in (fatal_bus_task, stopped_task) if waiter is not None),
            return_exceptions=True,
        )

        if exit_code != EXIT_RUNTIME_FATAL:
            if rm is not None:
                try:
                    await rm.prepare_shutdown()
                except Exception:
                    logger.error("Resource recovery cleanup failed", exc_info=True)

            if sm is not None:
                try:
                    await sm.stop()
                except Exception:
                    logger.error("State Manager cleanup failed", exc_info=True)

            if rm is not None:
                try:
                    report = await rm.stop_all()
                    for failure in report.failures:
                        logger.error(
                            "Resource stop failed: %s",
                            failure.key,
                            exc_info=(
                                type(failure.error),
                                failure.error,
                                failure.error.__traceback__,
                            ),
                        )
                except Exception:
                    logger.error("Resource shutdown failed", exc_info=True)

            if observer is not None:
                await observer.stop()
        await logging_runtime.flush(config.shutdown.logger_flush_timeout_seconds)
        logging_runtime.close()


def main() -> None:
    bootstrap_logging()
    raise SystemExit(asyncio.run(run_app()))


if __name__ == "__main__":
    main()
