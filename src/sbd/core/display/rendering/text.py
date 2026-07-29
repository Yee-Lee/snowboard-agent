"""
Text renderer.

Handles font loading, line-wrapping, colour, icon placement, and
multi-line layout.  Returns a PIL Image canvas that the Compositor
can overlay on any background.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont  # type: ignore

Color = Tuple[int, int, int]

# Fallback font paths (common on Raspberry Pi OS / Debian)
_FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(size: int, path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    if path:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            pass
    for p in _FONT_SEARCH_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except IOError:
            pass
    # Last resort: PIL built-in bitmap font (very limited character support)
    return ImageFont.load_default()


@dataclass
class TextStyle:
    """Visual properties for a block of text."""
    font_size: int = 12
    color: Color = (255, 255, 255)
    font_path: Optional[str] = None
    line_spacing: int = 4          # extra pixels between lines
    max_width: Optional[int] = None  # wrap at this pixel width; None = no wrap
    align: str = "left"            # "left" | "center" | "right"


class TextRenderer:
    """
    Renders a text string onto a transparent PIL canvas.

    Parameters
    ----------
    canvas_width, canvas_height:
        Size of the output image (RGBA so it can be alpha-composited).
    """

    def __init__(self, canvas_width: int, canvas_height: int) -> None:
        self.width = canvas_width
        self.height = canvas_height

    def render(
        self,
        text: str,
        style: TextStyle,
        x: int = 0,
        y: int = 0,
    ) -> Image.Image:
        """
        Draw *text* at (*x*, *y*) with the given style.

        Returns an RGBA canvas the same size as the renderer
        (transparent background, text drawn on top).
        """
        canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        font = _load_font(style.font_size, style.font_path)

        lines = self._wrap(text, font, style.max_width or (self.width - x))
        line_h = style.font_size + style.line_spacing

        for i, line in enumerate(lines):
            lx = x
            if style.align == "center":
                bbox = font.getbbox(line)
                lx = x + (self.width - x - (bbox[2] - bbox[0])) // 2
            elif style.align == "right":
                bbox = font.getbbox(line)
                lx = self.width - (bbox[2] - bbox[0]) - x
            draw.text((lx, y + i * line_h), line, font=font, fill=(*style.color, 255))

        return canvas

    # ------------------------------------------------------------------

    @staticmethod
    def _wrap(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
        """Word-wrap *text* to fit within *max_px* pixels wide."""
        if max_px <= 0:
            return [text]

        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            bbox = font.getbbox(candidate)
            if bbox[2] - bbox[0] <= max_px:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [text]
