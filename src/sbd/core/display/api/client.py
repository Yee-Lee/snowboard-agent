"""
DisplayClient — the public-facing API for all display callers.

Within the same Python process the client calls DisplayService directly.
Across processes it will transparently forward the same commands over a
Unix domain socket (not yet implemented; the interface is kept stable).

External callers only need to know about DisplayClient.  They must not
import anything from service/, rendering/, or hal/.

Example::

    from sbd.core.display import DisplayClient

    client = DisplayClient(service)
    client.set_status("thinking")
    client.notify("任務完成")
    client.show_alert("網路中斷")
    handle = await client.play_media("startup_animation")
    await handle.wait()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .commands import (
    DismissAlertCommand,
    NotifyCommand,
    PlayMediaCommand,
    SetStatusCommand,
    ShowAlertCommand,
)
from ..service.service import DisplayService, MediaHandle

logger = logging.getLogger(__name__)


class DisplayClient:
    """
    Thin facade that converts product-semantic API calls into typed
    commands and forwards them to DisplayService.

    The API is intentionally *fire-and-forget*: every call returns
    quickly (after the command is accepted).  Only play_media() returns
    a handle, which the caller may optionally await.
    """

    def __init__(self, service: DisplayService) -> None:
        self._service = service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(
        self,
        animation: str = "starry_night",
        owner: str = "default",
    ) -> None:
        """
        Set the persistent background status.

        Thread-safe: schedules the coroutine on the service event loop.
        """
        self._schedule(self._service.set_status(animation=animation, owner=owner))

    def notify(self, text: str, duration: float = 1.5) -> None:
        """Show a short text notification overlay."""
        self._schedule(self._service.notify(text=text, duration=duration))

    async def show_alert(
        self,
        text: str,
        duration: Optional[float] = None,
    ) -> str:
        """
        Show an exclusive alert.

        Returns the layer_id for later dismissal.
        Async because it returns a value from the service.
        """
        return await self._service.show_alert(text=text, duration=duration)

    async def dismiss_alert(self, layer_id: str) -> None:
        await self._service.dismiss_alert(layer_id)

    async def play_media(
        self,
        animation: str,
        duration: Optional[float] = None,
    ) -> MediaHandle:
        """
        Queue a media animation.

        Returns a MediaHandle.  Callers that need to wait for completion::

            handle = await client.play_media("startup_animation")
            await handle.wait()
        """
        return await self._service.play_media(animation=animation, duration=duration)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _schedule(self, coro) -> None:  # type: ignore[type-arg]
        """Fire-and-forget: schedule *coro* on the running event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            # No running loop — create one (sync context)
            asyncio.run(coro)
