import logging
import logging.handlers
import sys
import json
import re
import asyncio
import math
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Iterator

from sbd.core.config.models import LogConfig

SBD_LOGGER_NAME = "sbd"

REDACT_PATTERNS = [
    re.compile(r"(password=)([^ \n\r\t]+)", re.IGNORECASE),
    re.compile(r"(token=)([^ \n\r\t]+)", re.IGNORECASE),
    re.compile(r"(api_key=)([^ \n\r\t]+)", re.IGNORECASE),
    re.compile(r"(authorization=)([^ \n\r\t]+)", re.IGNORECASE),
]

_STANDARD_LOG_RECORD_KEYS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime"}
_SAFE_SENSITIVE_METADATA_KEYS = frozenset({"payload_bytes", "text_length"})
_SENSITIVE_EXTRA_KEY = re.compile(
    r"(?:^|_)(?:payload|prompt|transcript|arguments?|raw_output|audio|image|pcm|metadata|message_text)(?:_|$)",
    re.IGNORECASE,
)


def _safe_extra_value(value: Any) -> str | int | float | bool | None:
    """Return a bounded JSON scalar without inspecting arbitrary object reprs."""
    if value is None or type(value) in (int, bool):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else "invalid_extra"
    if type(value) is str:
        return redact_string(value)
    return "invalid_extra"


def _iter_safe_extras(record: logging.LogRecord) -> Iterator[tuple[str, Any]]:
    for key, value in record.__dict__.items():
        if key in _STANDARD_LOG_RECORD_KEYS:
            continue
        if not isinstance(key, str) or re.fullmatch(r"[a-z][a-z0-9_]*", key) is None:
            continue
        if key not in _SAFE_SENSITIVE_METADATA_KEYS and _SENSITIVE_EXTRA_KEY.search(key):
            continue
        yield key, _safe_extra_value(value)

def redact_string(s: Any) -> str:
    s = str(s)
    for p in REDACT_PATTERNS:
        s = p.sub(r"\1***", s)
    if len(s) > 512:
        s = s[:509] + "..."
    s = s.replace("\n", "\\n").replace("\r", "\\r")
    return s

class SbdTextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()
        ts = dt.isoformat(timespec='milliseconds')

        msg = redact_string(record.getMessage())
        base = f"{ts} {record.levelname} {record.name} {msg}"

        extras = [f"{key}={value}" for key, value in _iter_safe_extras(record)]

        if extras:
            base += " " + " ".join(extras)

        if record.exc_info:
            base += " " + redact_string(self.formatException(record.exc_info))

        return base

class SbdJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()
        ts = dt.isoformat(timespec='milliseconds')

        data: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": redact_string(record.getMessage())
        }

        for key, value in _iter_safe_extras(record):
            data[key] = value

        if record.exc_info:
            data["exception_info"] = redact_string(self.formatException(record.exc_info))

        try:
            return json.dumps(data)
        except Exception:
            return json.dumps({"timestamp": ts, "level": record.levelname, "logger": record.name, "message": "formatter_error"})


@dataclass(frozen=True, slots=True)
class LoggingRuntime:
    logger: logging.Logger
    handlers: tuple[logging.Handler, ...]

    async def flush(self, timeout_seconds: float) -> None:
        def _flush():
            for h in self.handlers:
                h.flush()
        try:
            await asyncio.wait_for(asyncio.to_thread(_flush), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            pass

    def close(self) -> None:
        for handler in self.handlers:
            handler.close()


def get_logger(name: str) -> logging.Logger:
    if not name.startswith(f"{SBD_LOGGER_NAME}."):
        name = f"{SBD_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def with_context(
    logger: logging.Logger,
    *,
    state: str | None = None,
    session_id: str | None = None,
    turn_id: int | None = None,
    correlation_id: int | None = None,
    worker_kind: str | None = None,
) -> logging.LoggerAdapter:
    extra: dict[str, Any] = {}
    if state is not None: extra["state"] = state
    if session_id is not None: extra["session_id"] = session_id
    if turn_id is not None: extra["turn_id"] = turn_id
    if correlation_id is not None: extra["correlation_id"] = correlation_id
    if worker_kind is not None: extra["worker_kind"] = worker_kind
    return logging.LoggerAdapter(logger, extra)


def bootstrap_logging() -> None:
    logger = logging.getLogger(SBD_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = True

    # Remove old handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(SbdTextFormatter())
    logger.addHandler(handler)


def configure_logging(config: LogConfig) -> LoggingRuntime:
    logger = logging.getLogger(SBD_LOGGER_NAME)

    # Clean up old handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()

    logger.setLevel(getattr(logging, config.level.upper()))
    logger.propagate = True

    formatter = SbdJsonFormatter() if config.format == "json" else SbdTextFormatter()

    if config.file is None:
        handler = logging.StreamHandler(sys.stderr)
    else:
        if config.rotate_max_bytes > 0 or config.rotate_backup_count > 0:
            handler = logging.handlers.RotatingFileHandler(
                config.file,
                maxBytes=config.rotate_max_bytes,
                backupCount=config.rotate_backup_count,
                encoding="utf-8"
            )
        else:
            handler = logging.FileHandler(config.file, encoding="utf-8")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return LoggingRuntime(logger=logger, handlers=(handler,))
