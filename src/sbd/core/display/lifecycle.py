"""Boot and shutdown fullscreen Blank ownership."""

from __future__ import annotations

from sbd.core.display.arbiter import DisplayArbiter
from sbd.core.display.hints import DisplayHint


BOOT_OWNER = "app.lifecycle.boot"
SHUTDOWN_OWNER = "app.lifecycle.shutdown"
BLANK = DisplayHint("fullscreen.blank")


class DisplayLifecycle:
    def __init__(self, arbiter: DisplayArbiter) -> None:
        self._arbiter = arbiter
        self._boot_owned = False
        self._shutdown_owned = False

    def begin_boot(self) -> bool:
        self._boot_owned = self._arbiter.request_fullscreen(BOOT_OWNER, BLANK)
        return self._boot_owned

    def finish_boot(self) -> None:
        if self._boot_owned:
            try:
                self._arbiter.release_fullscreen(BOOT_OWNER)
            finally:
                self._boot_owned = False

    def begin_shutdown(self) -> bool:
        self._shutdown_owned = self._arbiter.request_fullscreen(SHUTDOWN_OWNER, BLANK)
        return self._shutdown_owned
