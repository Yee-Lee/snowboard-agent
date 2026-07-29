"""
Video frame decoder.

Decodes a video file into a sequence of PIL Image frames using ffmpeg
(via subprocess pipe).  The decoder runs in a background thread and
feeds frames into an asyncio queue so the Service can consume them
at the panel's native frame rate.

Design notes
------------
- Frame decoding is decoupled from frame display; the Service decides
  when to call HAL.present().
- The decoder never touches the HAL directly.
- If the consumer is slower than the source, the queue fills and the
  decoder applies back-pressure (blocks on queue.put).
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

from PIL import Image  # type: ignore

logger = logging.getLogger(__name__)


class VideoDecoder:
    """
    Decodes a video file into PIL Image frames via an ffmpeg pipe.

    Usage::

        decoder = VideoDecoder("startup.mp4", width=128, height=128, fps=24)
        await decoder.start()
        async for frame in decoder:
            # frame is a PIL.Image.Image in "RGB" mode
            ...
        await decoder.stop()
    """

    def __init__(
        self,
        path: str | Path,
        width: int,
        height: int,
        fps: int = 24,
        queue_size: int = 8,
    ) -> None:
        self._path = Path(path)
        self._width = width
        self._height = height
        self._fps = fps
        self._queue: asyncio.Queue[Optional[Image.Image]] = asyncio.Queue(
            maxsize=queue_size
        )
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None  # type: ignore[type-arg]
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stopped = False

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background decoding thread."""
        self._loop = asyncio.get_running_loop()
        self._thread = threading.Thread(
            target=self._decode_thread, daemon=True, name="video-decoder"
        )
        self._thread.start()
        logger.info("[VideoDecoder] started for %s (%dx%d @ %d fps)",
                    self._path, self._width, self._height, self._fps)

    async def stop(self) -> None:
        """Stop decoding and clean up resources."""
        self._stopped = True
        if self._process:
            self._process.terminate()
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info("[VideoDecoder] stopped")

    def __aiter__(self) -> "VideoDecoder":
        return self

    async def __anext__(self) -> Image.Image:
        frame = await self._queue.get()
        if frame is None:
            raise StopAsyncIteration
        return frame

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _decode_thread(self) -> None:
        frame_size = self._width * self._height * 3  # RGB24

        cmd = [
            "ffmpeg",
            "-i", str(self._path),
            "-r", str(self._fps),
            "-f", "image2pipe",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{self._width}x{self._height}",
            "-",
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            assert self._process.stdout is not None

            while not self._stopped:
                raw = self._process.stdout.read(frame_size)
                if not raw or len(raw) != frame_size:
                    break  # EOF

                img = Image.frombytes("RGB", (self._width, self._height), raw)
                # Put frame into the asyncio queue from this background thread
                assert self._loop is not None
                future = asyncio.run_coroutine_threadsafe(
                    self._queue.put(img), self._loop
                )
                future.result()  # back-pressure: block until the queue accepts

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[VideoDecoder] error: %s", exc)
        finally:
            if self._process:
                self._process.stdout.close()  # type: ignore[union-attr]
                self._process.wait()
            # Signal end-of-stream
            if self._loop and not self._stopped:
                asyncio.run_coroutine_threadsafe(
                    self._queue.put(None), self._loop
                )
