"""
test_renderer_starry.py

Unit tests for the starry night renderer.

Enters the rendering layer directly (no HAL, no Service) to verify:
  - Frames are produced at expected size.
  - Rendering is deterministic (same t → same pixels).
  - Frames at different times differ from each other.
  - Frame-drop safety: render(t2) after skipping render(t1) still
    gives the same result as if render(t1) was called.
"""

import pytest
from PIL import Image

from sbd.core.display.rendering.animation import AnimationRenderer
from sbd.core.display.rendering.animations.starry_night import StarryNightAnimator


WIDTH, HEIGHT = 128, 128


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def animator() -> StarryNightAnimator:
    return StarryNightAnimator(width=WIDTH, height=HEIGHT, seed=42)


@pytest.fixture
def anim_renderer() -> AnimationRenderer:
    return AnimationRenderer(width=WIDTH, height=HEIGHT)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStarryNightAnimator:

    def test_frame_is_correct_size(self, animator):
        frame = animator.render(elapsed_time=0.0)
        assert isinstance(frame, Image.Image)
        assert frame.width == WIDTH
        assert frame.height == HEIGHT
        assert frame.mode == "RGB"

    def test_determinism(self, animator):
        """Same elapsed_time must always produce identical pixels."""
        f1 = animator.render(elapsed_time=1.234)
        f2 = animator.render(elapsed_time=1.234)
        assert f1.tobytes() == f2.tobytes()

    def test_different_times_differ(self, animator):
        f_early = animator.render(elapsed_time=0.5)
        f_late  = animator.render(elapsed_time=4.5)
        # Different times should produce visually different frames
        assert f_early.tobytes() != f_late.tobytes()

    def test_frame_drop_safety(self):
        """
        Render t=3.0 without ever calling t=1.0 or t=2.0.
        The result must match rendering t=3.0 on a fresh instance
        (i.e., no accumulated mutable state).
        """
        a1 = StarryNightAnimator(WIDTH, HEIGHT, seed=7)
        a2 = StarryNightAnimator(WIDTH, HEIGHT, seed=7)

        # a1: render every second
        a1.render(1.0)
        a1.render(2.0)
        f1 = a1.render(3.0)

        # a2: skip to t=3 directly
        f2 = a2.render(3.0)

        assert f1.tobytes() == f2.tobytes(), (
            "Frame-drop safety violated: skipping frames changed the output."
        )

    def test_warp_cycle_effect(self, animator):
        """Frames within the warp-speed phase should look different from cruise."""
        cruise = animator.render(elapsed_time=1.0)    # 1× warp
        warp   = animator.render(elapsed_time=3.5)   # ~4.5× warp
        assert cruise.tobytes() != warp.tobytes()


class TestAnimationRendererRegistry:

    def test_registered_animation(self, anim_renderer):
        """'starry_night' must be available in the registry."""
        frame = anim_renderer.render("starry_night", elapsed_time=0.0)
        assert isinstance(frame, Image.Image)

    def test_unknown_animation_raises(self, anim_renderer):
        with pytest.raises(KeyError, match="unknown_anim"):
            anim_renderer.render("unknown_anim", elapsed_time=0.0)

    def test_renderer_caches_instance(self, anim_renderer):
        """The same animator instance is reused across render() calls."""
        anim_renderer.render("starry_night", elapsed_time=0.0)
        anim_renderer.render("starry_night", elapsed_time=1.0)
        assert len(anim_renderer._instances) == 1

    def test_reset_creates_fresh_instance(self, anim_renderer):
        anim_renderer.render("starry_night", elapsed_time=0.0)
        anim_renderer.reset("starry_night")
        assert "starry_night" not in anim_renderer._instances
