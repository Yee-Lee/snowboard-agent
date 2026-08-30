#!/usr/bin/env python3
"""Bounded manual diagnostic for the physical conversation button."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sbd.core.config import load_config  # noqa: E402


async def wait_for_button(
    config: Any, *, timeout_seconds: float,
    gpio_factory: Callable[[Any], Any] | None = None,
) -> None:
    if config.core.gpio.driver != "gpiod":
        raise RuntimeError("core.gpio.driver must be gpiod")
    pin_config = config.core.gpio.pins.get("conversation")
    if pin_config is None:
        raise RuntimeError("core.gpio.pins.conversation is required")
    if gpio_factory is None:
        from sbd.core.gpio.gpiod.driver import GpiodGPIO
        gpio_factory = GpiodGPIO
    owner = gpio_factory(config.core.gpio)
    started = False
    registered = False
    pressed = asyncio.Event()

    async def callback(_event: Any) -> None:
        pressed.set()

    try:
        await asyncio.wait_for(owner.start(), timeout=5.0)
        started = True
        edge = "falling" if pin_config.active_low else "rising"
        await asyncio.wait_for(
            owner.register_input(
                pin_config.pin, edge, callback, debounce_ms=pin_config.debounce_ms
            ),
            timeout=5.0,
        )
        registered = True
        print(f"Press conversation button on BCM {pin_config.pin} within {timeout_seconds:g}s...")
        await asyncio.wait_for(pressed.wait(), timeout=timeout_seconds)
        print("Button press detected.")
    finally:
        if registered:
            await asyncio.wait_for(owner.unregister(pin_config.pin), timeout=5.0)
        if started:
            await asyncio.wait_for(owner.stop(), timeout=5.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)
    if (
        not args.config.is_file() or args.config.is_symlink()
        or not 0 < args.timeout_seconds <= 300
    ):
        print("ERROR: invalid config or timeout", file=sys.stderr)
        return 2
    try:
        config = load_config(
            local_path=args.config.resolve(), dotenv_path=Path(os.devnull), environ={}
        )
        asyncio.run(wait_for_button(config, timeout_seconds=args.timeout_seconds))
        return 0
    except TimeoutError:
        print("FAIL: button was not pressed before timeout", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
