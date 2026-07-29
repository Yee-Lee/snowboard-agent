"""
test_service_policy.py

Unit tests for the service scheduling policies (PolicyEngine).

Tests the four scheduling strategies:
  - STATUS    → latest-wins
  - OVERLAY   → composited, auto-expires
  - EXCLUSIVE → suspends others, resumes on remove
  - MEDIA     → queue, advances on completion
"""

import pytest

from sbd.core.display.service.policies import PolicyEngine
from sbd.core.display.service.scene import LayerState, LayerType, Scene, SceneLayer


def make_layer(
    layer_id: str,
    layer_type: LayerType,
    *,
    owner: str = "test",
    duration: float | None = None,
    priority: int = 0,
) -> SceneLayer:
    return SceneLayer(
        layer_id=layer_id,
        layer_type=layer_type,
        owner=owner,
        visible_duration=duration,
        priority=priority,
    )


@pytest.fixture
def scene() -> Scene:
    return Scene()


@pytest.fixture
def policy() -> PolicyEngine:
    return PolicyEngine()


# ---------------------------------------------------------------------------
# STATUS tests
# ---------------------------------------------------------------------------

class TestStatusPolicy:

    def test_status_becomes_visible(self, scene, policy):
        layer = make_layer("s1", LayerType.STATUS)
        policy.apply_status(scene, layer)
        assert layer.state == LayerState.VISIBLE

    def test_latest_wins_same_owner(self, scene, policy):
        """Second status from same owner cancels the first."""
        l1 = make_layer("s1", LayerType.STATUS, owner="ai")
        l2 = make_layer("s2", LayerType.STATUS, owner="ai")
        policy.apply_status(scene, l1)
        policy.apply_status(scene, l2)

        assert l1.state == LayerState.CANCELLED
        assert l2.state == LayerState.VISIBLE

    def test_different_owners_coexist(self, scene, policy):
        l1 = make_layer("s1", LayerType.STATUS, owner="ai")
        l2 = make_layer("s2", LayerType.STATUS, owner="ui")
        policy.apply_status(scene, l1)
        policy.apply_status(scene, l2)

        assert l1.state == LayerState.VISIBLE
        assert l2.state == LayerState.VISIBLE


# ---------------------------------------------------------------------------
# OVERLAY tests
# ---------------------------------------------------------------------------

class TestOverlayPolicy:

    def test_overlay_becomes_visible(self, scene, policy):
        layer = make_layer("o1", LayerType.OVERLAY, duration=1.5)
        policy.apply_overlay(scene, layer)
        assert layer.state == LayerState.VISIBLE

    def test_overlay_does_not_cancel_status(self, scene, policy):
        status = make_layer("s1", LayerType.STATUS)
        overlay = make_layer("o1", LayerType.OVERLAY, duration=1.0)
        policy.apply_status(scene, status)
        policy.apply_overlay(scene, overlay)

        assert status.state == LayerState.VISIBLE
        assert overlay.state == LayerState.VISIBLE
        assert len(scene.layers) == 2


# ---------------------------------------------------------------------------
# EXCLUSIVE tests
# ---------------------------------------------------------------------------

class TestExclusivePolicy:

    def test_exclusive_suspends_others(self, scene, policy):
        status = make_layer("s1", LayerType.STATUS)
        policy.apply_status(scene, status)

        alert = make_layer("a1", LayerType.EXCLUSIVE)
        policy.apply_exclusive(scene, alert)

        assert status.state == LayerState.SUSPENDED
        assert alert.state == LayerState.VISIBLE

    def test_remove_exclusive_resumes_suspended(self, scene, policy):
        status = make_layer("s1", LayerType.STATUS)
        policy.apply_status(scene, status)

        alert = make_layer("a1", LayerType.EXCLUSIVE)
        policy.apply_exclusive(scene, alert)
        policy.remove_exclusive(scene, "a1")

        assert status.state == LayerState.VISIBLE
        assert alert.state == LayerState.COMPLETED


# ---------------------------------------------------------------------------
# MEDIA queue tests
# ---------------------------------------------------------------------------

class TestMediaPolicy:

    def test_first_media_becomes_visible(self, scene, policy):
        m1 = make_layer("m1", LayerType.MEDIA)
        policy.apply_media(scene, m1)
        assert m1.state == LayerState.VISIBLE

    def test_second_media_is_queued(self, scene, policy):
        m1 = make_layer("m1", LayerType.MEDIA)
        m2 = make_layer("m2", LayerType.MEDIA)
        policy.apply_media(scene, m1)
        policy.apply_media(scene, m2)

        assert m1.state == LayerState.VISIBLE
        assert m2.state == LayerState.QUEUED

    def test_advance_queue_on_completion(self, scene, policy):
        m1 = make_layer("m1", LayerType.MEDIA)
        m2 = make_layer("m2", LayerType.MEDIA)
        policy.apply_media(scene, m1)
        policy.apply_media(scene, m2)

        m1.state = LayerState.COMPLETED
        policy.advance_media_queue(scene)

        assert m2.state == LayerState.VISIBLE


# ---------------------------------------------------------------------------
# Expiration sweep
# ---------------------------------------------------------------------------

class TestExpirationSweep:

    def test_expired_layer_is_completed(self, scene, policy):
        import time
        layer = make_layer("o1", LayerType.OVERLAY, duration=0.0)
        policy.apply_overlay(scene, layer)
        time.sleep(0.01)  # ensure it's past the duration

        completed = policy.expire_layers(scene)
        assert "o1" in completed
        assert layer.state == LayerState.COMPLETED

    def test_non_expired_layer_stays_visible(self, scene, policy):
        layer = make_layer("o1", LayerType.OVERLAY, duration=9999.0)
        policy.apply_overlay(scene, layer)

        completed = policy.expire_layers(scene)
        assert "o1" not in completed
        assert layer.state == LayerState.VISIBLE
