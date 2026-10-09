"""Behavioral checks for the disposable review player, not Core acceptance."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('m7_review', ROOT / 'poc_display/tools/m7_review.py')
review = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = review
spec.loader.exec_module(review)
from sbd.core.display.hal.mock import MockDisplayDevice


@pytest.fixture
def renderer():
    font_dir = Path(os.environ.get('M7_REVIEW_FONT_DIR', str(ROOT.parent / 'core/src/sbd/core/display/assets/fonts')))
    if not (font_dir / 'NotoSansTC-Regular.otf').exists():
        pytest.skip('offline baseline fonts unavailable; set M7_REVIEW_FONT_DIR')
    return review.Renderer(font_dir, review.Theme())


def test_rgb565_wire_order():
    im = Image.new('RGB', (3, 1))
    im.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255)])
    assert review.rgb565(im) == b'\xf8\x00\x07\xe0\x00\x1f'


def test_all_scenes_fit_and_blank_variants_are_black(renderer):
    assert {s.key.split('/')[0] for s in review.SCENES} == {f'SCN-{n:02}' for n in range(1, 10)}
    for s in review.SCENES:
        im = renderer.render(s, .4, True)
        assert im.size == (128, 128)
        assert len(review.rgb565(im)) == 32768
        if s.role == 'blank':
            assert im.getbbox() is None
    lines = renderer.lines('雨' * 200, renderer.main)
    assert len(lines) == 5
    assert lines[-1].endswith('…')
    assert all(renderer.main.getlength(line) <= 120 for line in lines)


def test_interrupt_does_not_use_speak_status_and_reply_has_distinct_color(renderer):
    interrupt = next(s for s in review.SCENES if s.key == 'SCN-07')
    assert interrupt.state == '中止中' and interrupt.icons == ('stop',)
    assert renderer.theme.input_fg != renderer.theme.reply_fg
    source = review.Scene('fixture', '', text='相同測試文字', role='input')
    reply = review.Scene('fixture', '', text=source.text, role='reply')
    assert renderer.render(source, 0).tobytes() != renderer.render(reply, 0).tobytes()


def test_motion_and_typewriter_only_change_intended_regions(renderer):
    for motion in ('ANI-003', 'ANI-001'):
        s = next(s for s in review.SCENES if s.motion == motion)
        first, later = renderer.render(s, 0), renderer.render(s, .15)
        assert first.crop((0, 0, 128, 20)).tobytes() != later.crop((0, 0, 128, 20)).tobytes()
        assert first.crop((0, 20, 128, 128)).tobytes() == later.crop((0, 20, 128, 128)).tobytes()
    s = next(s for s in review.SCENES if s.motion == 'ANI-005')
    empty = renderer.render(s, 0, True)
    part = renderer.render(s, .4, True)
    full = renderer.render(s, 3, True)
    assert empty.tobytes() != part.tobytes() != full.tobytes()
    assert full.tobytes() == renderer.render(s, 0, False).tobytes()
    assert empty.crop((0, 0, 128, 20)).tobytes() == full.crop((0, 0, 128, 20)).tobytes()


def test_control_navigation_pause_replay_and_effect():
    p = review.Player(elapsed=1.)
    p.command('b')
    assert p.index == 0
    p.command('n')
    assert p.index == 1 and p.elapsed == 0
    p.command('p')
    assert p.paused
    p.elapsed = 2
    p.command('r')
    assert p.elapsed == 0 and p.paused
    p.command('t')
    assert p.typewriter
    p.command('q')
    assert p.done


def test_theme_replacement_changes_visuals_without_changing_scene_ids(renderer, tmp_path):
    import json
    path = review.REVIEW_DIR / 'themes/THM-baseline.json'
    data = json.loads(path.read_text())
    data['theme'].update(theme_id='THM-test', input_fg='#FFFF70', main_size=16, main_line_height=24)
    alternate = tmp_path / 'THM-test.json'
    alternate.write_text(json.dumps(data))
    theme = review.load_theme(alternate)
    changed = review.Renderer(Path(renderer.main.path).parent, theme)
    s = next(s for s in review.SCENES if s.role == 'input')
    assert changed.render(s, 0).tobytes() != renderer.render(s, 0).tobytes()
    for scene in review.SCENES:
        assert changed.render(scene, .2, True).size == (128, 128)
    data['theme']['animations']['ANI-001']['preview']['cycle'] = 0
    alternate.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='positive finite'):
        review.load_theme(alternate)


def test_custom_theme_icon_is_used_and_escapes_are_rejected(renderer, tmp_path):
    from dataclasses import replace
    Image.new('RGBA', (12, 12), '#FF00FF').save(tmp_path / 'idle.png')
    theme = replace(renderer.theme, asset_root=str(tmp_path), icon_files={'idle': 'idle.png'})
    custom = review.Renderer(Path(renderer.main.path).parent, theme)
    assert custom.icon('idle', 0).getpixel((0, 0)) == (255, 0, 255)
    bad = replace(theme, icon_files={'idle': '../outside.png'})
    with pytest.raises(ValueError, match='within the theme directory'):
        review.Renderer(Path(renderer.main.path).parent, bad)


def test_mock_player_finishes_black_and_closes_without_redundant_static_flush(renderer):
    device = MockDisplayDevice()
    asyncio.run(review.play(device, renderer, fps=15, max_seconds=.15))
    assert device.frame_count == 2  # One static logo, one final blank.
    assert device.last_frame == bytes(32768)
    with pytest.raises(RuntimeError):
        device.show()


def test_show_failure_still_closes_device(renderer):
    class BrokenDevice(MockDisplayDevice):
        def show(self):
            raise RuntimeError('synthetic failure')
        async def stop(self):
            self.stopped = True
            await super().stop()
    device = BrokenDevice()
    with pytest.raises(RuntimeError, match='synthetic failure'):
        asyncio.run(review.play(device, renderer, max_seconds=.1))
    assert device.stopped


def test_start_failure_still_attempts_stop(renderer):
    class BrokenStart(MockDisplayDevice):
        async def start(self):
            raise RuntimeError('start failure')
        async def stop(self):
            self.stopped = True
    device = BrokenStart()
    with pytest.raises(RuntimeError, match='start failure'):
        asyncio.run(review.play(device, renderer, max_seconds=.1))
    assert device.stopped


def test_task_cancellation_clears_and_closes(renderer):
    device = MockDisplayDevice()
    async def cancel_run():
        task = asyncio.create_task(review.play(device, renderer, max_seconds=10))
        await asyncio.sleep(.03)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel_run())
    assert device.last_frame == bytes(32768)
    with pytest.raises(RuntimeError):
        device.show()
