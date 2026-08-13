"""M3 selected OLED renderer tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from sbd.core.display import DisplayHint, DisplayHintError, Oled128Renderer, RenderModel


def _model(*, state="IDLE", main=None, fullscreen=None):
    return RenderModel(
        status_slots=(("state", DisplayHint("status.state", {"state": state})),),
        main=main,
        fullscreen=fullscreen,
    )


def test_m3_rend_001() -> None:
    renderer = Oled128Renderer()
    for model in (
        _model(),
        _model(main=DisplayHint("main.text", {"text": "固定內容"})),
        _model(fullscreen=DisplayHint("fullscreen.blank")),
    ):
        assert len(renderer.render(size=(128, 128), model=model)) == 32768
    with pytest.raises(DisplayHintError, match="unknown"):
        renderer.validate(DisplayHint("main.error", {"category": "x", "summary": "y"}))
    with pytest.raises(DisplayHintError, match="invalid fields"):
        renderer.validate(DisplayHint("main.text", {"text": "x", "extra": 1}))


def test_m3_rend_002() -> None:
    renderer = Oled128Renderer()
    hashes = {
        state: hashlib.sha256(renderer.render(size=(128, 128), model=_model(state=state))).hexdigest()
        for state in ("IDLE", "WAKE", "PERCEPTION", "THINK", "ACTION", "ERROR")
    }
    assert len(set(hashes.values())) == 6
    unsupported = renderer.render(
        size=(128, 128),
        model=_model(main=DisplayHint("main.text", {"text": "A\U0010ffffB"})),
    )
    replacement = renderer.render(
        size=(128, 128),
        model=_model(main=DisplayHint("main.text", {"text": "A□B"})),
    )
    assert unsupported == replacement


def test_m3_rend_003() -> None:
    frame = Oled128Renderer().render(
        size=(128, 128), model=_model(fullscreen=DisplayHint("fullscreen.blank"))
    )
    assert frame == bytes(32768)


def test_m3_rend_004() -> None:
    renderer = Oled128Renderer()
    long_frame = renderer.render(
        size=(128, 128),
        model=_model(main=DisplayHint("main.text", {"text": "測試內容" * 100})),
    )
    empty_frame = renderer.render(
        size=(128, 128),
        model=_model(main=DisplayHint("main.text", {"text": "   \n  "})),
    )
    baseline = renderer.render(size=(128, 128), model=_model(main=None))
    assert long_frame != baseline
    assert empty_frame == baseline
    assert long_frame == renderer.render(
        size=(128, 128),
        model=_model(main=DisplayHint("main.text", {"text": "測試內容" * 100})),
    )


def test_m3_rend_005() -> None:
    root = Path("src/sbd/core/display/assets/fonts")
    expected = {
        "NotoSansTC-Regular.otf": "5bab0cb3c1cf89dde07c4a95a4054b195afbcfe784d69d75c340780712237537",
        "NotoSansTC-Medium.otf": "bf206dca0975779bac71cb49a037a364156ca98a0c431b1b7d6b29fb8952ac7e",
    }
    assert {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in expected
    } == expected
    assert (root / "OFL-1.1.txt").is_file()
