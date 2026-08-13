"""Single-threaded display ownership and atomic flush arbitration."""

from __future__ import annotations

import logging
import threading

from sbd.core.display.base import DisplayDevice
from sbd.core.display.hints import DisplayHint, UnknownDisplaySlot
from sbd.core.display.renderer import DisplayRenderer, RenderModel


SLOT_REGISTRY = ("clock", "state", "volume", "connection", "capability", "error")


class DisplayArbiter:
    def __init__(self, device: DisplayDevice, renderer: DisplayRenderer, *, logger=None) -> None:
        self._device = device
        self._renderer = renderer
        self._logger = logger or logging.getLogger(__name__)
        self._slots: dict[str, DisplayHint] = {}
        self._main: DisplayHint | None = None
        self._fullscreen_owner: str | None = None
        self._fullscreen: DisplayHint | None = None
        self._started = False
        self._ever_started = False
        self._rendering_enabled = True
        self._thread_id: int | None = None

    async def start(self) -> None:
        self._thread_id = threading.get_ident()
        self._started = True
        self._ever_started = True
        self._render_current()

    async def stop(self) -> None:
        if not self._started:
            return
        self._assert_loop_thread()
        if self._rendering_enabled:
            try:
                self._device.clear()
                self._device.show()
            except Exception as exc:
                self._degrade(exc)
        self._started = False

    def write_status_slot(self, slot_id: str, hint: DisplayHint | None) -> None:
        if slot_id not in SLOT_REGISTRY:
            raise UnknownDisplaySlot(slot_id)
        if not self._ready_for_write():
            return
        if hint is not None:
            self._renderer.validate(hint)
            self._slots[slot_id] = hint
        else:
            self._slots.pop(slot_id, None)
        if self._fullscreen_owner is None:
            self._render_current()

    def write_main(self, hint: DisplayHint | None) -> None:
        if not self._ready_for_write():
            return
        if hint is not None:
            self._renderer.validate(hint)
        self._main = hint
        if self._fullscreen_owner is None:
            self._render_current()

    def request_fullscreen(self, owner_id: str, hint: DisplayHint) -> bool:
        if not self._ready_for_write():
            return False
        if not owner_id:
            raise ValueError("fullscreen owner_id must be non-empty")
        if self._fullscreen_owner not in {None, owner_id}:
            return False
        self._renderer.validate(hint)
        self._fullscreen_owner = owner_id
        self._fullscreen = hint
        self._render_current()
        return True

    def release_fullscreen(self, owner_id: str) -> None:
        if not self._ready_for_write():
            return
        if owner_id != self._fullscreen_owner:
            return
        self._fullscreen_owner = None
        self._fullscreen = None
        self._render_current()

    def snapshot(self) -> RenderModel:
        return self._model()

    def _ready_for_write(self) -> bool:
        self._assert_loop_thread()
        if self._started:
            return True
        if not self._ever_started:
            raise RuntimeError("DisplayArbiter has not started")
        self._logger.debug("ignoring display intent after arbiter stop")
        return False

    def _assert_loop_thread(self) -> None:
        if self._thread_id is not None and threading.get_ident() != self._thread_id:
            raise RuntimeError("DisplayArbiter must be called from its event-loop thread")

    def _model(self) -> RenderModel:
        return RenderModel(
            status_slots=tuple(
                (slot, self._slots[slot]) for slot in SLOT_REGISTRY if slot in self._slots
            ),
            main=self._main,
            fullscreen=self._fullscreen if self._fullscreen_owner is not None else None,
        )

    def _render_current(self) -> None:
        if not self._rendering_enabled:
            return
        try:
            size = self._device.size()
            if size == (0, 0):
                return
            pixels = self._renderer.render(size=size, model=self._model())
            self._device.clear()
            self._device.write_pixels(pixels)
            self._device.show()
        except Exception as exc:
            self._degrade(exc)

    def _degrade(self, exc: Exception) -> None:
        if self._rendering_enabled:
            self._rendering_enabled = False
            self._logger.error(
                "display rendering disabled component=display.arbiter error_type=%s",
                type(exc).__name__,
            )
