"""Compatibility exports for the canonical owner-defined exceptions.

New code should import these types from their owner modules.  This facade keeps
legacy imports type-identical instead of defining a second taxonomy.
"""

from sbd.core.config.validate import ConfigError
from sbd.core.event_bus import FatalDispatchError
from sbd.core.resource_manager.errors import RecoveryFatalError, StartupError
from sbd.core.state_manager.convergence import ConvergenceFatalError
from sbd.core.state_manager.exceptions import (
    ReasonerContractViolation,
    StateManagerFatalError,
    StateManagerInvariantViolation,
    WorkerContractViolation,
)


class ExternalMessageNotFound(Exception):
    """External message not found."""


class DisplayHintError(Exception):
    """Display hint error."""



class ActionPayloadValidationError(Exception):
    """Action payload validation error; canonical owner arrives in M2."""


__all__ = [
    "ActionPayloadValidationError",
    "ConfigError",
    "ConvergenceFatalError",
    "DisplayHintError",
    "ExternalMessageNotFound",
    "FatalDispatchError",
    "ReasonerContractViolation",
    "RecoveryFatalError",
    "StartupError",
    "StateManagerFatalError",
    "StateManagerInvariantViolation",
    "WorkerContractViolation",
]
