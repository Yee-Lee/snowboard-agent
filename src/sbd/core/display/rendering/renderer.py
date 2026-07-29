"""
Core renderer and compositing types.

The Renderer converts a Scene (from the Service layer) at a given
elapsed_time into a single RGB565 frame ready for the HAL.

Key design decisions
--------------------
- Rendering is deterministic: given the same Scene + elapsed_time it
  always produces the same frame, so the Service can freely drop frames
  on slow panels and the next frame will still be temporally correct.
- The Compositor merges background, status, and overlay layers onto a
  single Canvas before converting to RGB565.
- All pixel maths happens in 8-bit RGB; conversion to RGB565 is the
  last step just before handing off to the HAL.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image, ImageDraw  # type: ignore


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# A logical canvas at 8-bit RGB depth (PIL Image in "RGB" mode).
Canvas = Image.Image

# A hardware-ready RGB565 frame (bytes, row-major, big-endian).
Frame = bytes


@dataclass
class RenderContext:
    """Everything a renderer needs to produce one frame."""
    width: int
    height: int
    elapsed_time: float           # seconds since animation/content started
    background: Optional[Canvas] = None


# ---------------------------------------------------------------------------
# RGB888 → RGB565 helpers
# ---------------------------------------------------------------------------

def canvas_to_rgb565(canvas: Canvas) -> Frame:
    """Convert a PIL RGB canvas to a big-endian RGB565 byte string."""
    rgb = canvas.convert("RGB")
    data = rgb.tobytes()
    n = len(data) // 3
    out = bytearray(n * 2)
    for i in range(n):
        r, g, b = data[i * 3], data[i * 3 + 1], data[i * 3 + 2]
        color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out[i * 2]     = (color >> 8) & 0xFF
        out[i * 2 + 1] = color & 0xFF
    return bytes(out)


def blank_canvas(width: int, height: int) -> Canvas:
    return Image.new("RGB", (width, height), (0, 0, 0))


# ---------------------------------------------------------------------------
# Compositor
# ---------------------------------------------------------------------------

class Compositor:
    """
    Merges multiple Canvas layers into one.

    Layers are composited in order (back to front) using alpha blending
    when the layer has an alpha channel, or simple paste otherwise.
    """

    def composite(
        self,
        width: int,
        height: int,
        layers: list[tuple[Canvas, tuple[int, int]]],
    ) -> Canvas:
        """
        Merge *layers* onto a black background.

        Parameters
        ----------
        width, height:
            Output canvas size.
        layers:
            List of (canvas, (x, y)) tuples.  Composited front-to-back.
        """
        result = blank_canvas(width, height)
        for layer, (x, y) in layers:
            if layer.mode == "RGBA":
                result.paste(layer, (x, y), mask=layer)
            else:
                result.paste(layer, (x, y))
        return result


# ---------------------------------------------------------------------------
# Main Renderer
# ---------------------------------------------------------------------------

class Renderer:
    """
    Converts a Scene description + elapsed_time into an RGB565 Frame.

    Usage::

        renderer = Renderer(width=128, height=128)
        frame = renderer.render(scene, elapsed_time=t)

    The renderer delegates actual drawing to specialised sub-renderers
    (TextRenderer, AnimationRenderer, etc.) and then composites their
    outputs.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._compositor = Compositor()

    def render_blank(self) -> Frame:
        """Return a blank (black) frame."""
        return bytes(self.width * self.height * 2)

    def render_canvas(self, canvas: Canvas) -> Frame:
        """Convert a pre-drawn Canvas to an RGB565 Frame."""
        if canvas.width != self.width or canvas.height != self.height:
            canvas = canvas.resize((self.width, self.height))
        return canvas_to_rgb565(canvas)

    def composite_and_render(
        self,
        layers: list[tuple[Canvas, tuple[int, int]]],
    ) -> Frame:
        """Composite layers and convert to RGB565."""
        canvas = self._compositor.composite(self.width, self.height, layers)
        return canvas_to_rgb565(canvas)
