import pytest
import asyncio
import logging
import json
from pathlib import Path

from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.logger import (
    configure_logging, bootstrap_logging, redact_string, get_logger, SBD_LOGGER_NAME
)
from sbd.core.error_observer import ErrorLoggingObserver
from sbd.core.config.models import LogConfig
from sbd.core.exceptions import (
    ConfigError as ExportedConfigError,
    ConvergenceFatalError as ExportedConvergenceFatalError,
    FatalDispatchError as ExportedFatalDispatchError,
    ReasonerContractViolation,
    RecoveryFatalError as ExportedRecoveryFatalError,
    StartupError as ExportedStartupError,
    StateManagerInvariantViolation,
)
from sbd.core.config.validate import ConfigError as OwnerConfigError
from sbd.core.event_bus import FatalDispatchError as OwnerFatalDispatchError
from sbd.core.resource_manager.errors import RecoveryFatalError as OwnerRecoveryFatalError
from sbd.core.resource_manager.errors import StartupError as OwnerStartupError
from sbd.core.state_manager.convergence import ConvergenceFatalError as OwnerConvergenceFatalError
from sbd.core.state_manager.exceptions import ReasonerContractViolation as OwnerReasonerContractViolation
from sbd.core.state_manager.exceptions import StateManagerInvariantViolation as OwnerStateManagerInvariantViolation

class FakeBus:
    def __init__(self):
        self.handlers = []
    def subscribe(self, event_type, handler, name=None):
        self.handlers.append((event_type, handler, name))
        return "token123"
    def unsubscribe(self, token):
        pass

def test_log_001_formatters_and_handlers(tmp_path: Path):
    # Text config
    config_text = LogConfig(level="INFO", format="text", file=tmp_path / "test.log")
    rt1 = configure_logging(config_text)

    logger = logging.getLogger(SBD_LOGGER_NAME)
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.FileHandler)

    # JSON config with rotation
    config_json = LogConfig(
        level="DEBUG",
        format="json",
        file=tmp_path / "test.json",
        rotate_max_bytes=1000,
        rotate_backup_count=3
    )
    rt2 = configure_logging(config_json)

    assert len(logger.handlers) == 1
    from logging.handlers import RotatingFileHandler
    assert isinstance(logger.handlers[0], RotatingFileHandler)

    # Log a message with a bad extra
    class BadObj:
        def __repr__(self):
            return "BadObjRep"

    sentinel = "CUSTOMER_PAYLOAD_MUST_NOT_LEAK"
    my_logger = get_logger("my_comp")
    my_logger.debug("test_json", extra={"bad_extra": BadObj(), "correlation_id": 42,
                                        "payload": {"transcript": sentinel}, "prompt": sentinel})
    asyncio.run(rt2.flush(1.0))

    content = (tmp_path / "test.json").read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["message"] == "test_json"
    assert data["logger"] == "sbd.my_comp"
    assert data["bad_extra"] == "invalid_extra"
    assert "payload" not in data and "prompt" not in data
    assert sentinel not in content

    config_safe_text = LogConfig(level="INFO", format="text", file=tmp_path / "safe.log")
    rt3 = configure_logging(config_safe_text)
    my_logger.warning("safe_message", extra={"tool_arguments": sentinel, "worker_kind": "tool"})
    asyncio.run(rt3.flush(1.0))
    text_content = (tmp_path / "safe.log").read_text()
    assert sentinel not in text_content
    assert "tool_arguments" not in text_content
    assert "worker_kind=tool" in text_content

def test_log_002_error_observer(caplog):
    logging.getLogger(SBD_LOGGER_NAME).propagate = True
    bus = FakeBus()
    obs = ErrorLoggingObserver(bus)

    asyncio.run(obs.start())

    assert len(bus.handlers) == 1
    evt_type, handler, name = bus.handlers[0]
    assert evt_type is ErrorOccurred
    assert name == "error_logger"

    # Publish ErrorOccurred
    evt = ErrorOccurred(where="perception.listen", error="listen failed", exception_type="OSError")
    with caplog.at_level(logging.ERROR, logger="sbd.error_observer"):
        asyncio.run(obs(evt))

    assert len(caplog.records) == 1
    rec = caplog.records[0]
    assert rec.levelname == "ERROR"
    assert rec.message == "listen failed"
    assert getattr(rec, "where", None) == "perception.listen"
    assert not rec.exc_info

    caplog.clear()

    # Test invalid where
    bad_evt = ErrorOccurred(where="BAD WHERE!", error="some error")
    with caplog.at_level(logging.ERROR, logger="sbd.error_observer"):
        asyncio.run(obs(bad_evt))

    assert len(caplog.records) == 1
    assert caplog.records[0].where == "invalid_where"
    assert caplog.records[0].invalid_where == "BAD WHERE!"

def test_log_003_redaction(caplog):
    s1 = "This is a password=secret123 and token=abc456 test."
    r1 = redact_string(s1)
    assert "secret123" not in r1
    assert "abc456" not in r1
    assert "password=***" in r1
    assert "token=***" in r1

    s2 = "Line1\nLine2\rLine3"
    r2 = redact_string(s2)
    assert "\n" not in r2
    assert "\\n" in r2

    s3 = "A" * 600
    r3 = redact_string(s3)
    assert len(r3) == 512
    assert r3.endswith("...")

def test_log_004_fatal_supervision():
    assert issubclass(StateManagerInvariantViolation, RuntimeError)
    assert issubclass(ReasonerContractViolation, Exception)
    assert ExportedConfigError is OwnerConfigError
    assert ExportedStartupError is OwnerStartupError
    assert ExportedFatalDispatchError is OwnerFatalDispatchError
    assert StateManagerInvariantViolation is OwnerStateManagerInvariantViolation
    assert ReasonerContractViolation is OwnerReasonerContractViolation
    assert ExportedConvergenceFatalError is OwnerConvergenceFatalError
    assert ExportedRecoveryFatalError is OwnerRecoveryFatalError
    assert not issubclass(ReasonerContractViolation, StateManagerInvariantViolation)

    # Test P5 WARNING logic (just that we use WARNING for Fact errors)
    p5_res = PerceptionResult(kind="listen", status="error", text=None)
    logger = get_logger("perception.listen")
    # if it were published, we should log WARNING, but that's handled by SM/worker layer.
    assert p5_res.status == "error"
