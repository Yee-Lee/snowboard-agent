"""API sub-package — public entry point for all display callers."""

from .client import DisplayClient
from .commands import (
    SetStatusCommand,
    NotifyCommand,
    ShowAlertCommand,
    PlayMediaCommand,
    DismissAlertCommand,
)

__all__ = [
    "DisplayClient",
    "SetStatusCommand",
    "NotifyCommand",
    "ShowAlertCommand",
    "PlayMediaCommand",
    "DismissAlertCommand",
]
