"""
Scheduling policies for the Service layer.

These are pure functions / small classes that the Service delegates to
when it needs to decide what to do with a new command.
"""

from __future__ import annotations

from .scene import LayerState, LayerType, Scene, SceneLayer


class PolicyEngine:
    """
    Applies product-level scheduling policies to incoming layers.

    The architecture specifies these policies:

    STATUS    → latest-wins; replaces any existing STATUS from the same owner
    OVERLAY   → short-lived, composited on top; may merge with latest-wins
    EXCLUSIVE → immediately visible; suspends all lower-priority layers
    MEDIA     → queued; visible one at a time

    All decisions mutate the *scene* in-place and return the resulting
    layer state.
    """

    # ------------------------------------------------------------------ #
    #  STATUS
    # ------------------------------------------------------------------ #

    def apply_status(self, scene: Scene, layer: SceneLayer) -> None:
        """
        Latest-wins: the new STATUS layer replaces any existing STATUS
        layer from the same owner and becomes immediately visible.
        """
        assert layer.layer_type == LayerType.STATUS
        # Cancel any prior STATUS from the same owner
        for existing in list(scene.layers):
            if (existing.layer_type == LayerType.STATUS
                    and existing.owner == layer.owner
                    and existing.layer_id != layer.layer_id):
                existing.state = LayerState.CANCELLED
        layer.state = LayerState.VISIBLE
        scene.add_or_replace(layer)

    # ------------------------------------------------------------------ #
    #  OVERLAY
    # ------------------------------------------------------------------ #

    def apply_overlay(self, scene: Scene, layer: SceneLayer) -> None:
        """
        Add an overlay on top of the current scene.
        The overlay will expire once its visible_duration elapses.
        """
        assert layer.layer_type == LayerType.OVERLAY
        layer.state = LayerState.VISIBLE
        scene.layers.append(layer)

    # ------------------------------------------------------------------ #
    #  EXCLUSIVE (alert)
    # ------------------------------------------------------------------ #

    def apply_exclusive(self, scene: Scene, layer: SceneLayer) -> None:
        """
        An EXCLUSIVE layer hides all other layers while it is visible.
        Other layers are SUSPENDED (not CANCELLED) so they can resume
        when the exclusive layer is removed.
        """
        assert layer.layer_type == LayerType.EXCLUSIVE
        for existing in scene.layers:
            if existing.state == LayerState.VISIBLE:
                existing.state = LayerState.SUSPENDED
        layer.state = LayerState.VISIBLE
        scene.layers.append(layer)

    def remove_exclusive(self, scene: Scene, layer_id: str) -> None:
        """
        Remove an EXCLUSIVE layer and resume all SUSPENDED layers.

        The resumed content is re-rendered fresh — we never restore old
        frame buffers.
        """
        layer = scene.get(layer_id)
        if layer:
            layer.state = LayerState.COMPLETED
        for existing in scene.layers:
            if existing.state == LayerState.SUSPENDED:
                existing.state = LayerState.VISIBLE

    # ------------------------------------------------------------------ #
    #  MEDIA queue
    # ------------------------------------------------------------------ #

    def apply_media(self, scene: Scene, layer: SceneLayer) -> None:
        """
        Queue a MEDIA layer.  If nothing is currently playing, make it
        visible immediately; otherwise it waits in QUEUED state.
        """
        assert layer.layer_type == LayerType.MEDIA
        playing = any(
            l.layer_type == LayerType.MEDIA and l.state == LayerState.VISIBLE
            for l in scene.layers
        )
        layer.state = LayerState.QUEUED if playing else LayerState.VISIBLE
        scene.layers.append(layer)

    def advance_media_queue(self, scene: Scene) -> None:
        """
        Called when a MEDIA layer completes.  Promotes the next queued
        MEDIA layer to VISIBLE.
        """
        queued = [
            l for l in scene.layers
            if l.layer_type == LayerType.MEDIA and l.state == LayerState.QUEUED
        ]
        queued.sort(key=lambda l: l.priority)
        if queued:
            queued[0].state = LayerState.VISIBLE

    # ------------------------------------------------------------------ #
    #  Expiration sweep
    # ------------------------------------------------------------------ #

    def expire_layers(self, scene: Scene) -> list[str]:
        """
        Mark any timed-out VISIBLE layers as COMPLETED.

        Returns the list of completed layer IDs.
        """
        completed: list[str] = []
        for layer in scene.layers:
            if layer.state == LayerState.VISIBLE and layer.is_expired():
                layer.state = LayerState.COMPLETED
                completed.append(layer.layer_id)
        return completed
