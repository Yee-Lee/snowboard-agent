"""
Starry Night animation.

A 3-D star-field with a cyclic warp-speed effect, ported from the
original test_starring_night.py and redesigned to be:

  - **Deterministic**: every frame is computed purely from
    ``elapsed_time``, a fixed ``seed``, and initial star parameters.
    There is no mutable per-frame state that accumulates — so the
    Service can skip frames freely and the next rendered frame will
    still correspond to the correct point in time.

  - **Registered**: decorated with ``@register("starry_night")`` so
    ``AnimationRenderer.render("starry_night", elapsed_time)`` works
    without any explicit import.

Algorithm
---------
Each star is assigned immutable attributes at construction time:
    x0, y0   — initial normalised position ∈ (−1, 1)
    z0       — initial depth ∈ (0.1, 2.0)
    speed    — base z-velocity (units/sec)

At time *t* the star's depth is:

    z(t) = z0 − speed × ∫₀ᵗ warp_factor(τ) dτ   (mod period)

Rather than integrating analytically (the warp function is piecewise),
we compute the star's *virtual age* using the accumulated phase of the
warp cycle.  This gives us a cheap O(N) per-frame computation without
any mutable star state.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw  # type: ignore

from sbd.core.display.rendering.animation import register, Animator

# ---------------------------------------------------------------------------
# Warp schedule (matches the original 8-second cycle)
# ---------------------------------------------------------------------------

_WARP_CYCLE = 8.0  # seconds


def _warp_factor(t: float) -> float:
    """
    Return the instantaneous warp multiplier at time *t* (seconds).

    Cycle:  0-2 s  → cruise (1×)
            2-4 s  → accelerate to 4.5×
            4-4.5 s→ peak (4.5×)
            4.5-8 s→ decelerate to 1×
    """
    cycle = t % _WARP_CYCLE
    if cycle < 2.0:
        return 1.0
    if cycle < 4.0:
        progress = (cycle - 2.0) / 2.0
        return 1.0 + (progress ** 3) * 3.5
    if cycle < 4.5:
        return 4.5
    progress = (cycle - 4.5) / 3.5
    return 4.5 - (progress ** 1.5) * 3.5


def _integrated_warp(t: float, steps: int = 200) -> float:
    """
    Numerically integrate ∫₀ᵗ warp_factor(τ) dτ using the trapezoidal rule.

    This gives the total "virtual distance" each star has travelled by
    time *t*, making the animation frame-drop-safe.
    """
    if t <= 0:
        return 0.0
    dt = t / steps
    total = 0.0
    prev = _warp_factor(0.0)
    for i in range(1, steps + 1):
        curr = _warp_factor(i * dt)
        total += (prev + curr) * 0.5 * dt
        prev = curr
    return total


# ---------------------------------------------------------------------------
# Star data
# ---------------------------------------------------------------------------

@dataclass
class _Star:
    x0: float   # normalised initial x ∈ (−1, 1)
    y0: float   # normalised initial y ∈ (−1, 1)
    z0: float   # initial depth ∈ (0.1, 2.0)
    speed: float  # z-decrement per unit of integrated warp

    def position_at(self, integrated_warp: float) -> tuple[float, float, float]:
        """Return (x0, y0, z) where z = (z0 − speed × D) wrapped to (0, 2)."""
        D = self.speed * integrated_warp
        # Wrap z so the star "loops" when it passes the viewer
        z = (self.z0 - D % 2.0) % 2.0
        if z <= 0.01:
            z = 1.9  # reset to back of the field
        return self.x0, self.y0, z


# ---------------------------------------------------------------------------
# Animator implementation
# ---------------------------------------------------------------------------

class StarryNightAnimator:
    """
    Implements the Animator protocol for the starry night animation.

    Parameters
    ----------
    width, height:
        Pixel dimensions of the output canvas.
    num_stars:
        Number of stars to simulate.
    seed:
        RNG seed for reproducible star layout.
    """

    def __init__(
        self,
        width: int,
        height: int,
        num_stars: int = 150,
        seed: int = 42,
    ) -> None:
        self._width = width
        self._height = height
        self._stars = self._init_stars(num_stars, seed)

    @staticmethod
    def _init_stars(n: int, seed: int) -> list[_Star]:
        rng = random.Random(seed)
        stars = []
        for _ in range(n):
            stars.append(_Star(
                x0=rng.uniform(-1.0, 1.0),
                y0=rng.uniform(-1.0, 1.0),
                z0=rng.uniform(0.1, 2.0),
                speed=rng.uniform(0.01, 0.03),
            ))
        return stars

    def render(self, elapsed_time: float) -> Image.Image:
        """
        Render the star field at *elapsed_time* seconds.

        Deterministic: called with the same elapsed_time → same image.
        """
        img = Image.new("RGB", (self._width, self._height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        D = _integrated_warp(elapsed_time)
        cx, cy = self._width / 2, self._height / 2

        for star in self._stars:
            _, _, z = star.position_at(D)

            sx = int((star.x0 / z) * cx + cx)
            sy = int((star.y0 / z) * cy + cy)

            if not (0 <= sx < self._width and 0 <= sy < self._height):
                continue

            brightness = int((1.0 - z / 2.0) * 255)
            r = int(brightness * 0.5)
            g = int(brightness * 0.9)
            b = brightness

            size = 2 if z < 0.4 else 1
            draw.rectangle([sx, sy, sx + size - 1, sy + size - 1], fill=(r, g, b))

        return img


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@register("starry_night")
def _factory(width: int, height: int, **kwargs: object) -> StarryNightAnimator:
    return StarryNightAnimator(width=width, height=height, **kwargs)
