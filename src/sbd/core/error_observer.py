import re
from typing import Any
from sbd.core.events import ErrorOccurred
from sbd.core.faults import safe_category_for_code
from sbd.core.logger import get_logger

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
            extra["invalid_where"] = True
            where = "invalid_where"

        logger.error(
            event.error,
            extra={
                "where": where,
                "code": event.code,
                "backend_disposition": event.backend_disposition,
                "recovery_keys": ",".join(sorted(event.recovery_keys)),
                "safe_category": safe_category_for_code(event.code),
                **extra,
            },
        )
