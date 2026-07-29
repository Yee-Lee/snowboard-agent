"""
DisplayService — the single arbiter of the display hardware.

Responsibilities
----------------
- Receives commands from all sources via a single asyncio Queue.
- Maintains the Scene (layers, priorities, lifecycle).
- Decides scheduling policy via PolicyEngine.
- Runs the render loop via RenderScheduler.
- Is the ONLY component allowed to call HAL.present().

Thread / task model (single process)
-------------------------------------
    API caller ──► command_queue ──► _command_loop task  (updates scene)
                                                          │
                                           RenderScheduler._produce_loop
                                                          │
                                           RenderScheduler._consume_loop ──► HAL

All HAL calls happen from within the service's event-loop; the
CtypesDisplayDevice dispatches them to a thread-pool executor so the
event loop is never blocked.

Usage::

    device = create_device("mock")
    service = DisplayService(device)
    await service.start()

    # From any coroutine (or sync code via asyncio.run_coroutine_threadsafe):
    await service.set_status("thinking")
    await service.notify("任務完成", duration=1.5)
    await service.show_alert("網路中斷")
    handle = await service.play_media("startup_animation")
    await handle.wait()

    await service.stop()
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from PIL import Image  # type: ignore

from ..hal.protocol import DisplayDevice
from ..rendering.animation import AnimationRenderer
from ..rendering.renderer import Renderer, canvas_to_rgb565
from ..rendering.text import TextRenderer, TextStyle
from .policies import PolicyEngine
from .scene import LayerState, LayerType, Scene, SceneLayer
from .scheduler import RenderScheduler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Media handle
# ---------------------------------------------------------------------------

class MediaHandle:
    """
    Returned by play_media().  Callers can await handle.wait() to block
    until the media finishes (or is cancelled).
    """

    def __init__(self, layer_id: str) -> None:
        self.layer_id = layer_id
        self._done = asyncio.Event()

    def _complete(self) -> None:
        self._done.set()

    async def wait(self) -> None:
        await self._done.wait()

    def cancel(self) -> None:
        self._done.set()

    @property
    def is_done(self) -> bool:
        return self._done.is_set()


# ---------------------------------------------------------------------------
# Internal command types
# ---------------------------------------------------------------------------

@dataclass
class _CmdStatus:
    animation: str
    owner: str

@dataclass
class _CmdNotify:
    text: str
    duration: float

@dataclass
class _CmdAlert:
    text: str
    duration: Optional[float]
    layer_id: str

@dataclass
class _CmdMedia:
    animation: str
    duration: Optional[float]
    layer_id: str
    handle: MediaHandle

@dataclass
class _CmdDismissAlert:
    layer_id: str

_Command = _CmdStatus | _CmdNotify | _CmdAlert | _CmdMedia | _CmdDismissAlert


# ---------------------------------------------------------------------------
# DisplayService
# ---------------------------------------------------------------------------

class DisplayService:
    """
    The single owner of the display hardware.

    See module docstring for architecture and usage notes.
    """

    def __init__(
        self,
        device: DisplayDevice,
        target_fps: int = 30,
    ) -> None:
        self._device = device
        self._target_fps = target_fps

        w = device.info.logical_width
        h = device.info.logical_height
        self._renderer = Renderer(w, h)
        self._anim_renderer = AnimationRenderer(w, h)
        self._text_renderer = TextRenderer(w, h)
        self._policy = PolicyEngine()
        self._scene = Scene()

        self._command_queue: asyncio.Queue[_Command] = asyncio.Queue()
        self._scheduler: Optional[RenderScheduler] = None
        self._start_time = time.monotonic()

        self._running = False
        self._tasks: list[asyncio.Task] = []  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Open the hardware device and start the render loop."""
        await self._device.open()
        self._start_time = time.monotonic()
        self._running = True

        self._scheduler = RenderScheduler(
            target_fps=self._target_fps,
            producer=self._produce_frame,
            consumer=self._ship_frame,
            start_time=self._start_time,
        )

        self._tasks = [
            asyncio.create_task(self._command_loop(), name="display-cmd"),
            asyncio.create_task(self._scheduler.run(), name="display-render"),
        ]
        logger.info("[DisplayService] started")

    async def stop(self) -> None:
        """Stop rendering and close the hardware device."""
        self._running = False
        if self._scheduler:
            self._scheduler.stop()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._device.clear()
        await self._device.close()
        logger.info("[DisplayService] stopped")

    # ------------------------------------------------------------------
    # Public API — called by DisplayClient (or directly in tests)
    # ------------------------------------------------------------------

    async def set_status(
        self,
        animation: str = "starry_night",
        owner: str = "default",
    ) -> None:
        """
        Set the persistent background status animation.

        Same owner → latest-wins; no queue.
        """
        await self._command_queue.put(_CmdStatus(animation=animation, owner=owner))

    async def notify(self, text: str, duration: float = 1.5) -> None:
        """
        Show a short text overlay.  Does not interrupt the background.
        """
        await self._command_queue.put(_CmdNotify(text=text, duration=duration))

    async def show_alert(
        self,
        text: str,
        duration: Optional[float] = None,
    ) -> str:
        """
        Show an exclusive alert that covers all other content.

        Returns a layer_id that can be passed to dismiss_alert().
        If *duration* is given, the alert auto-dismisses after that many seconds.
        """
        layer_id = str(uuid.uuid4())
        await self._command_queue.put(
            _CmdAlert(text=text, duration=duration, layer_id=layer_id)
        )
        return layer_id

    async def dismiss_alert(self, layer_id: str) -> None:
        await self._command_queue.put(_CmdDismissAlert(layer_id=layer_id))

    async def play_media(
        self,
        animation: str,
        duration: Optional[float] = None,
    ) -> MediaHandle:
        """
        Queue a media animation.

        Returns a MediaHandle; call ``await handle.wait()`` to block
        until the animation completes.
        """
        layer_id = str(uuid.uuid4())
        handle = MediaHandle(layer_id)
        await self._command_queue.put(
            _CmdMedia(
                animation=animation,
                duration=duration,
                layer_id=layer_id,
                handle=handle,
            )
        )
        return handle

    # ------------------------------------------------------------------
    # Command processing loop
    # ------------------------------------------------------------------

    async def _command_loop(self) -> None:
        while self._running:
            try:
                cmd = await asyncio.wait_for(self._command_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                self._sweep()
                continue

            self._apply_command(cmd)
            self._sweep()

    def _apply_command(self, cmd: _Command) -> None:
        if isinstance(cmd, _CmdStatus):
            layer = SceneLayer(
                layer_id=f"status-{cmd.owner}",
                layer_type=LayerType.STATUS,
                animation_name=cmd.animation,
                owner=cmd.owner,
                priority=0,
            )
            self._policy.apply_status(self._scene, layer)

        elif isinstance(cmd, _CmdNotify):
            layer = SceneLayer(
                layer_id=str(uuid.uuid4()),
                layer_type=LayerType.OVERLAY,
                text=cmd.text,
                priority=10,
                visible_duration=cmd.duration,
            )
            self._policy.apply_overlay(self._scene, layer)

        elif isinstance(cmd, _CmdAlert):
            layer = SceneLayer(
                layer_id=cmd.layer_id,
                layer_type=LayerType.EXCLUSIVE,
                text=cmd.text,
                priority=20,
                visible_duration=cmd.duration,
                interruption_policy="deny",
            )
            self._policy.apply_exclusive(self._scene, layer)

        elif isinstance(cmd, _CmdDismissAlert):
            self._policy.remove_exclusive(self._scene, cmd.layer_id)

        elif isinstance(cmd, _CmdMedia):
            layer = SceneLayer(
                layer_id=cmd.layer_id,
                layer_type=LayerType.MEDIA,
                animation_name=cmd.animation,
                priority=5,
                visible_duration=cmd.duration,
            )
            # Attach handle for completion notification
            layer.__dict__["_handle"] = cmd.handle
            self._policy.apply_media(self._scene, layer)

    def _sweep(self) -> None:
        """Expire timed-out layers and advance the media queue."""
        completed = self._policy.expire_layers(self._scene)
        for lid in completed:
            layer = self._scene.get(lid)
            if layer and layer.layer_type == LayerType.MEDIA:
                handle: Optional[MediaHandle] = layer.__dict__.get("_handle")
                if handle:
                    handle._complete()
                self._policy.advance_media_queue(self._scene)
            # Exclusive layers: resume suspended layers
            if layer and layer.layer_type == LayerType.EXCLUSIVE:
                self._policy.remove_exclusive(self._scene, lid)

        # GC completed/cancelled layers
        self._scene.layers = [
            l for l in self._scene.layers
            if l.state not in (LayerState.COMPLETED, LayerState.CANCELLED)
        ]

    # ------------------------------------------------------------------
    # Render pipeline
    # ------------------------------------------------------------------

    def _produce_frame(self, elapsed_time: float) -> Optional[Image.Image]:
        """
        Called by the RenderScheduler at target_fps.

        Compose all visible layers into a single PIL Image.
        """
        visible = self._scene.sorted_layers()
        if not visible:
            return None

        layers_canvases: list[tuple[Image.Image, tuple[int, int]]] = []
        w = self._device.info.logical_width
        h = self._device.info.logical_height

        for layer in visible:
            canvas: Optional[Image.Image] = None

            if layer.animation_name:
                try:
                    canvas = self._anim_renderer.render(
                        layer.animation_name, elapsed_time - (time.monotonic() - layer.start_time)
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("[Service] render error for %s: %s", layer.animation_name, exc)

            elif layer.text:
                canvas = self._text_renderer.render(
                    layer.text,
                    TextStyle(font_size=14, color=(255, 255, 255)),
                    x=4, y=h // 2 - 8,
                )

            if canvas is not None:
                layers_canvases.append((canvas, (0, 0)))

        if not layers_canvases:
            return None

        return self._renderer._compositor.composite(w, h, layers_canvases)

    async def _ship_frame(self, canvas: Image.Image) -> None:
        """
        Convert the composited canvas to RGB565 and send to the HAL.

        This is the ONLY place HAL.present() is called.
        """
        frame = canvas_to_rgb565(canvas)
        await self._device.present(frame)
