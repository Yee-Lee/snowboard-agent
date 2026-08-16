"""Renderer for the selected 128x128 RGB565 OLED profile."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from sbd.core.display.hints import DisplayHint, DisplayHintError


@dataclass(frozen=True, slots=True)
class RenderModel:
    status_slots: tuple[tuple[str, DisplayHint], ...]
    main: DisplayHint | None
    fullscreen: DisplayHint | None


class DisplayRenderer(Protocol):
    def validate(self, hint: DisplayHint) -> None: ...
    def render(self, *, size: tuple[int, int], model: RenderModel) -> bytes: ...


_STATES = {
    "IDLE": "待命",
    "WAKE": "準備中",
    "PERCEPTION": "接收中",
    "THINK": "思考中",
    "ACTION": "回應中",
    "ERROR": "錯誤",
}


class Oled128Renderer:
    """Synchronous, HAL-independent implementation of DSP-PROFILE-OLED-128."""

    def __init__(self, *, assets_dir: Path | None = None) -> None:
        root = assets_dir or Path(__file__).with_name("assets") / "fonts"
        self._regular = ImageFont.truetype(str(root / "NotoSansTC-Regular.otf"), 14)
        self._medium = ImageFont.truetype(str(root / "NotoSansTC-Medium.otf"), 12)
        self._missing_key = self._glyph_key(self._regular, "\U0010ffff")

    def validate(self, hint: DisplayHint) -> None:
        schemas = {
            "status.text": {"text": str},
            "status.state": {"state": str},
            "main.text": {"text": str},
            "fullscreen.blank": {},
        }
        schema = schemas.get(hint.template)
        if schema is None:
            raise DisplayHintError(f"unknown display template: {hint.template}")
        if set(hint.data) != set(schema):
            raise DisplayHintError(f"{hint.template} has invalid fields")
        for field, expected in schema.items():
            if type(hint.data[field]) is not expected:
                raise DisplayHintError(f"{hint.template}.{field} has invalid type")
        if hint.template == "status.state" and hint.data["state"] not in _STATES:
            raise DisplayHintError("status.state contains an unknown state")

    def render(self, *, size: tuple[int, int], model: RenderModel) -> bytes:
        if size != (128, 128):
            raise DisplayHintError("DSP-PROFILE-OLED-128 requires size (128, 128)")
        hints = [hint for _, hint in model.status_slots]
        if model.main is not None:
            hints.append(model.main)
        if model.fullscreen is not None:
            hints.append(model.fullscreen)
        for hint in hints:
            self.validate(hint)

        image = Image.new("RGB", size, (0, 0, 0))
        if model.fullscreen is not None:
            return self._rgb565(image)

        draw = ImageDraw.Draw(image)
        state = next(
            (hint for slot, hint in model.status_slots if slot == "state"), None
        )
        if state is not None:
            text = _STATES[state.data["state"]]
            draw.text((4, 2), text, font=self._medium, fill=(255, 255, 255))
        draw.line((0, 20, 127, 20), fill=(48, 52, 58), width=1)

        if model.main is not None and model.main.template == "main.text":
            text = self._replace_missing(model.main.data["text"].strip())
            if text:
                for index, line in enumerate(self._wrap(draw, text, 120, 5)):
                    draw.text((4, 24 + index * 20), line, font=self._regular, fill=(255, 255, 255))
        return self._rgb565(image)

    def _replace_missing(self, text: str) -> str:
        return "".join(
            char
            if char.isspace()
            else ("□" if self._glyph_key(self._regular, char) == self._missing_key else char)
            for char in text
        )

    def _wrap(self, draw: ImageDraw.ImageDraw, text: str, width: int, max_lines: int) -> list[str]:
        lines: list[str] = []
        current = ""
        consumed = 0
        for char in text:
            if char == "\n":
                lines.append(current)
                current = ""
                consumed += 1
            elif draw.textlength(current + char, font=self._regular) <= width:
                current += char
                consumed += 1
            else:
                lines.append(current)
                current = char
                consumed += 1
            if len(lines) == max_lines:
                break
        if len(lines) < max_lines and (current or not lines):
            lines.append(current)
        if consumed < len(text):
            ellipsis = "…"
            last = lines[-1]
            while last and draw.textlength(last + ellipsis, font=self._regular) > width:
                last = last[:-1]
            lines[-1] = last + ellipsis
        return lines[:max_lines]

    @staticmethod
    def _glyph_key(font, char: str) -> tuple[tuple[int, int], bytes]:
        mask = font.getmask(char)
        return mask.size, bytes(mask)

    @staticmethod
    def _rgb565(image: Image.Image) -> bytes:
        result = bytearray()
        pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
        for red, green, blue in pixels:
            value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
            result.extend(value.to_bytes(2, "big"))
        return bytes(result)
