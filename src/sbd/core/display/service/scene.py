"""
Scene and layer data model for the Service layer.

The Service maintains a scene graph of layers.  Each layer has a type
that determines scheduling policy (status / overlay / exclusive / media).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class LayerType(Enum):
    STATUS    = auto()   # persistent state; latest-wins
    OVERLAY   = auto()   # short-lived overlay; composited on top of STATUS
    EXCLUSIVE = auto()   # hides all other layers; used for alerts
    MEDIA     = auto()   # queued media (animation / video)


class LayerState(Enum):
    QUEUED    = auto()
    VISIBLE   = auto()
    SUSPENDED = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass
class SceneLayer:
    """A single content layer managed by the Service."""

    layer_id: str
    layer_type: LayerType

    # What to show — either a named animation or a static PIL canvas
    animation_name: Optional[str] = None      # e.g. "starry_night"
    text: Optional[str] = None               # e.g. "任務完成"
    video_path: Optional[str] = None         # for MEDIA layers

    # Scheduling
    state: LayerState = LayerState.QUEUED
    priority: int = 0                        # higher = drawn last (on top)
    owner: Optional[str] = None             # who set this layer

    # Timing
    start_time: float = field(default_factory=time.monotonic)
    visible_duration: Optional[float] = None  # None = infinite
    interruption_policy: str = "allow"       # "allow" | "deny"

    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    def is_expired(self) -> bool:
        if self.visible_duration is None:
            return False
        return self.elapsed() >= self.visible_duration


@dataclass
class Scene:
    """
    The current display scene: an ordered collection of active layers.

    Layers are rendered in priority order (lowest priority first = bottom).
    """
    layers: list[SceneLayer] = field(default_factory=list)

    def sorted_layers(self) -> list[SceneLayer]:
        return sorted(
            [l for l in self.layers if l.state == LayerState.VISIBLE],
            key=lambda l: l.priority,
        )

    def add_or_replace(self, layer: SceneLayer) -> None:
        """For STATUS layers: replace any existing layer of the same type."""
        self.layers = [
            l for l in self.layers
            if not (l.layer_type == layer.layer_type == LayerType.STATUS
                    and l.owner == layer.owner)
        ]
        self.layers.append(layer)

    def remove(self, layer_id: str) -> None:
        self.layers = [l for l in self.layers if l.layer_id != layer_id]

    def get(self, layer_id: str) -> Optional[SceneLayer]:
        for l in self.layers:
            if l.layer_id == layer_id:
                return l
        return None
