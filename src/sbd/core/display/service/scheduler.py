"""
Render scheduler.

Drives the render loop at a target FPS and applies the
latest-frame-wins drop policy when the HAL is too slow.

Architecture:
    render task  ──(latest frame)──►  native I/O owner  ──►  HAL

If the native I/O owner is still writing the previous frame when a new
one is ready, the old pending frame is discarded and only the newest
frame is queued.  This prevents animation lag on slow panels.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable, Optional

from PIL import Image  # type: ignore

logger = logging.getLogger(__name__)

# Frame producer: given elapsed_time, returns a PIL canvas (or None to skip)
FrameProducer = Callable[[float], Optional[Image.Image]]

# Frame consumer: given a PIL canvas, ships it to the HAL
FrameConsumer = Callable[[Image.Image], Awaitable[None]]


class RenderScheduler:
    """
    Fixed-rate render loop with latest-frame-wins drop policy.

    Parameters
    ----------
    target_fps:
        Desired render rate.  The scheduler will sleep between frames to
        hit this rate, and will drop frames when the consumer is slow.
    producer:
        Callable ``(elapsed_time) → PIL.Image | None``.
        Called on every tick; return None to skip the frame.
    consumer:
        Async callable ``(PIL.Image) → None``.
        This is the "native I/O owner" path; must not be called from
        more than one coroutine at a time.
    start_time:
        Monotonic start time for elapsed_time calculation.
        Defaults to now.
    """

    def __init__(
        self,
        target_fps: int,
        producer: FrameProducer,
        consumer: FrameConsumer,
        start_time: Optional[float] = None,
    ) -> None:
        self._target_fps = target_fps
        self._frame_time = 1.0 / target_fps
        self._producer = producer
        self._consumer = consumer
        self._start_time = start_time or time.monotonic()
        self._running = False
        self._pending_frame: Optional[Image.Image] = None
        self._io_busy = False
        # FPS tracking
        self._fps_frame_count: int = 0
        self._fps_window_start: float = 0.0

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Run the scheduler loop until stop() is called."""
        self._running = True
        logger.info("[Scheduler] starting at %d FPS", self._target_fps)
        try:
            await asyncio.gather(
                self._produce_loop(),
                self._consume_loop(),
            )
        finally:
            self._running = False
            logger.info("[Scheduler] stopped")

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # Internal loops
    # ------------------------------------------------------------------

    async def _produce_loop(self) -> None:
        """Generate frames at target_fps and store the latest one."""
        self._fps_window_start = time.monotonic()
        self._fps_frame_count = 0
        while self._running:
            tick_start = time.monotonic()
            elapsed = tick_start - self._start_time

            frame = self._producer(elapsed)
            if frame is not None:
                # Latest-frame-wins: overwrite any un-consumed pending frame
                self._pending_frame = frame
                self._fps_frame_count += 1

            # Print actual FPS to terminal once per second
            now = time.monotonic()
            window = now - self._fps_window_start
            if window >= 1.0:
                actual_fps = self._fps_frame_count / window
                print(f"\r[FPS] {actual_fps:.1f} / {self._target_fps} target", end="", flush=True)
                self._fps_frame_count = 0
                self._fps_window_start = now

            work = time.monotonic() - tick_start
            sleep = self._frame_time - work
            if sleep > 0:
                await asyncio.sleep(sleep)

    async def _consume_loop(self) -> None:
        """Ship pending frames to the HAL as fast as the HAL can accept."""
        while self._running:
            if self._pending_frame is not None and not self._io_busy:
                frame = self._pending_frame
                self._pending_frame = None
                self._io_busy = True
                try:
                    await self._consumer(frame)
                finally:
                    self._io_busy = False
            else:
                await asyncio.sleep(0)  # yield to other coroutines
