"""
Typed command schema for the Display API.

Commands are the *only* things that cross the API → Service boundary.
They describe *what the caller wants* in product-semantic terms, not
*how* the display should be updated.

These dataclasses double as the serialisation format when transmitting
commands over a Unix domain socket (via JSON or msgpack).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SetStatusCommand:
    """
    Set the persistent background status animation.

    Same *owner* → latest-wins; older status from the same owner is replaced.
    """
    animation: str = "starry_night"  # registered animation name
    owner: str = "default"           # caller identity


@dataclass
class NotifyCommand:
    """
    Show a short text notification as an overlay.

    Does not interrupt the background animation.
    """
    text: str
    duration: float = 1.5  # visible seconds


@dataclass
class ShowAlertCommand:
    """
    Show an exclusive full-screen alert.

    Suspends all other content until the alert is dismissed.
    """
    text: str
    duration: Optional[float] = None  # None = must be manually dismissed


@dataclass
class DismissAlertCommand:
    """Manually dismiss an active alert by its layer_id."""
    layer_id: str


@dataclass
class PlayMediaCommand:
    """
    Queue a media animation (or video) for playback.

    Returns a MediaHandle via the client.
    """
    animation: str
    duration: Optional[float] = None  # None = play once / based on clip length
