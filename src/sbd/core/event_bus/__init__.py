"""Public Event Bus API."""

from .bus import EventBus, FatalDispatchError, Subscription

__all__ = ["EventBus", "FatalDispatchError", "Subscription"]
