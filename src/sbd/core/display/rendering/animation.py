"""
Animation renderer base class and registry.

Each animation is a pure function of (elapsed_time, width, height) →
PIL Image.  This makes them deterministic and frame-drop-safe: if the
panel is slow, the service skips frames and the next rendered frame
still corresponds to the correct point in time.

Usage::

    from rendering.animation import AnimationRenderer
    from rendering.animations import starry_night

    renderer = AnimationRenderer(128, 128)
    canvas = renderer.render("starry_night", elapsed_time=2.5)
"""

from __future__ import annotations

import importlib
import logging
from typing import Callable, Protocol

from PIL import Image  # type: ignore

logger = logging.getLogger(__name__)

# An animation factory is a callable that returns a per-instance animator.
# The animator itself is a callable: (elapsed_time: float) -> PIL.Image.Image
AnimationFactory = Callable[..., "Animator"]


class Animator(Protocol):
    """Protocol for a stateful (but deterministic) animation object."""

    def render(self, elapsed_time: float) -> Image.Image:
        """
        Render the animation at *elapsed_time* seconds.

        Must be deterministic: same inputs → same output.
        """
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_registry: dict[str, AnimationFactory] = {}


def register(name: str) -> Callable[[AnimationFactory], AnimationFactory]:
    """Decorator to register an animation factory under *name*."""
    def decorator(factory: AnimationFactory) -> AnimationFactory:
        _registry[name] = factory
        return factory
    return decorator


def _load_builtin_animations() -> None:
    """Lazy-import all built-in animations so they self-register."""
    builtin = [
        "sbd.core.display.rendering.animations.starry_night",
    ]
    for module in builtin:
        try:
            importlib.import_module(module)
        except ImportError as exc:
            logger.warning("Could not load animation module %s: %s", module, exc)


# ---------------------------------------------------------------------------
# AnimationRenderer
# ---------------------------------------------------------------------------

class AnimationRenderer:
    """
    Creates and drives named animation instances.

    Each animation is instantiated once (per AnimationRenderer instance)
    and then called with the current elapsed_time on every render call.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._instances: dict[str, Animator] = {}

        _load_builtin_animations()

    def render(self, name: str, elapsed_time: float, **kwargs: object) -> Image.Image:
        """
        Render frame at *elapsed_time* for animation *name*.

        The animator is created on first use and reused on subsequent
        calls (its internal seed stays the same for determinism).
        """
        if name not in self._instances:
            if name not in _registry:
                raise KeyError(
                    f"Unknown animation '{name}'. "
                    f"Available: {list(_registry)}"
                )
            factory = _registry[name]
            self._instances[name] = factory(
                width=self.width, height=self.height, **kwargs
            )

        return self._instances[name].render(elapsed_time)

    def reset(self, name: str) -> None:
        """Discard the cached animator so it restarts from t=0."""
        self._instances.pop(name, None)
