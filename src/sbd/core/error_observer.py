import re
from typing import Any
from sbd.core.events import ErrorOccurred
from sbd.core.logger import get_logger, redact_string

logger = get_logger("error_observer")

WHERE_REGEX = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")

class ErrorLoggingObserver:
    """Canonical ERROR log writer for ErrorOccurred events."""

    def __init__(self, bus: Any) -> None:
        self.bus = bus
        self._token: Any = None

    async def start(self) -> None:
        self._token = self.bus.subscribe(
            ErrorOccurred,
            self,
            name="error_logger"
        )

    async def stop(self) -> None:
        if self._token:
            self.bus.unsubscribe(self._token)
            self._token = None

    async def __call__(self, event: ErrorOccurred) -> None:
        if type(event) is not ErrorOccurred:
            return

        where = event.where
        extra: dict[str, Any] = {}
        if not WHERE_REGEX.match(where):
            extra["invalid_where"] = redact_string(where)
            where = "invalid_where"

        error_msg = redact_string(event.error)

        if event.exception_type:
            extra["exception_type"] = event.exception_type

        logger.error(error_msg, extra={"where": where, **extra})
