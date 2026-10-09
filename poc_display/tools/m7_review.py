#!/usr/bin/env python3
"""Reusable offline theme review player; synthetic fixtures, not Core integration."""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import math
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sbd.core.display.hal.factory import create_device
from sbd.core.display.hal.profiles import load_display_config


@dataclass(frozen=True)
class Scene:
    key: str
    label: str
    state: str = ''
    text: str = ''
    icons: tuple[str, ...] = ()
    role: str = 'normal'
    motion: str = ''


REVIEW_DIR = Path(__file__).resolve().parents[1] / 'review'

def load_scenes():
    data = json.loads((REVIEW_DIR / 'scenes.json').read_text())
    if data['schema_version'] != 1:
        raise ValueError('unsupported scene schema')
    scenes = tuple(Scene(**{**row, 'icons': tuple(row['icons'])}) for row in data['scenes'])
    if len({row.key for row in scenes}) != len(scenes):
        raise ValueError('duplicate scene keys')
    return scenes

SCENES = load_scenes()


@dataclass(frozen=True)
class Theme:
    # Preview values only: colors, animation timing and logo are not product decisions.
    status_bg: str = '#000000'
    status_fg: str = '#FFFFFF'
    main_bg: str = '#000000'
    main_fg: str = '#FFFFFF'
    input_fg: str = '#FFFFFF'
    reply_fg: str = '#90EE90'
    error_fg: str = '#FFB000'
    logo: str = 'Snowboard'
    theme_id: str = 'THM-baseline'
    status_size: int = 12
    status_line_height: int = 16
    main_size: int = 14
    main_line_height: int = 20
    error_size: int = 14
    error_line_height: int = 20
    icon_size: int = 12
    icon_gap: int = 4
    icon_files: dict = field(default_factory=dict)
    asset_root: str = ''
    animations: dict = field(default_factory=dict)

    def animation(self, animation_id):
        defaults = {'ANI-001': {'kind':'flip', 'cycle':1.5, 'flip_seconds':.3},
                    'ANI-003': {'kind':'breath', 'cycle':1.5},
                    'ANI-005': {'kind':'typewriter', 'char_seconds':.08, 'max_seconds':3.}}
        return self.animations.get(animation_id, {}).get('preview', defaults.get(animation_id, {'kind':'static'}))


def load_theme(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['schema_version'] != 1:
        raise ValueError('unsupported theme schema')
    if 'asset_root' in data['theme']:
        raise ValueError('asset root is resolved from the theme location')
    theme = Theme(**data['theme'], asset_root=str(path.resolve().parent))
    if not theme.theme_id.startswith('THM-'):
        raise ValueError('theme_id must start with THM-')
    for key in ('status_bg','status_fg','main_bg','main_fg','input_fg','reply_fg','error_fg'):
        if len(ImageColor.getrgb(getattr(theme, key))) != 3:
            raise ValueError('theme colors must be opaque RGB')
    if theme.status_bg != '#000000' or theme.main_bg != '#000000':
        raise ValueError('current OLED profile requires black backgrounds')
    if not (1 <= theme.icon_size <= 16 and 0 <= theme.icon_gap <= 8):
        raise ValueError('invalid icon dimensions')
    for size, height, max_height in ((theme.status_size, theme.status_line_height, 16),
                                  (theme.main_size, theme.main_line_height, 100),
                                  (theme.error_size, theme.error_line_height, 100)):
        if not (6 <= size <= height <= max_height):
            raise ValueError('invalid theme typography')
    allowed = {'ANI-001','ANI-002','ANI-003','ANI-004','ANI-005'}
    if set(theme.animations) - allowed:
        raise ValueError('new ANI identity requires scene/renderer support')
    for spec in theme.animations.values():
        preview = spec.get('preview', {})
        if preview.get('kind') not in ('static','flip','breath','typewriter'):
            raise ValueError('unsupported preview effect')
        for key in ('cycle','flip_seconds','char_seconds','max_seconds'):
            value = preview.get(key, 1.)
            if not isinstance(value, (int,float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('animation times must be positive finite numbers')
    return theme


class Renderer:
    def __init__(self, font_dir: Path, theme: Theme):
        self.theme = theme
        self.status = ImageFont.truetype(str(font_dir / 'NotoSansTC-Medium.otf'), theme.status_size)
        self.main = ImageFont.truetype(str(font_dir / 'NotoSansTC-Regular.otf'), theme.main_size)
        self.error = ImageFont.truetype(str(font_dir / 'NotoSansTC-Medium.otf'), theme.error_size)
        self.icon_assets = {}
        for name, filename in theme.icon_files.items():
            if name not in {'idle','wake','mic','message','camera','think','tool','speak','error','stop'}:
                raise ValueError('unknown icon role')
            root = Path(theme.asset_root).resolve()
            path = (root / filename).resolve()
            if not path.is_relative_to(root):
                raise ValueError('icon files must be within the theme directory')
            with Image.open(path) as asset:
                if asset.size != (theme.icon_size, theme.icon_size):
                    raise ValueError('theme icon dimensions must match icon_size')
                self.icon_assets[name] = asset.convert('RGBA')

    @staticmethod
    def lines(text, font, max_lines=5):
        result = []
        for paragraph in text.split('\n'):
            line = ''
            for char in paragraph:
                if font.getlength(line + char) > 120 and line:
                    result.append(line)
                    line = ''
                line += char
            result.append(line)
        if len(result) > max_lines:
            result = result[:max_lines]
            while font.getlength(result[-1] + '…') > 120:
                result[-1] = result[-1][:-1]
            result[-1] += '…'
        return result

    def icon(self, kind, elapsed):
        if kind in self.icon_assets:
            im = Image.new('RGBA', (self.theme.icon_size, self.theme.icon_size), self.theme.status_bg)
            asset = self.icon_assets[kind].copy()
            if kind == 'wake':
                effect = self.theme.animation('ANI-003')
                if effect['kind'] == 'breath':
                    level = .4 + .6 * (1 - math.cos(2 * math.pi * elapsed / effect.get('cycle',1.5))) / 2
                    asset.putalpha(asset.getchannel('A').point(lambda value: round(value * level)))
            im.alpha_composite(asset)
            im = im.convert('RGB')
            if kind == 'think':
                effect = self.theme.animation('ANI-001')
                if effect['kind'] == 'flip':
                    turn = min(1., (elapsed % effect.get('cycle',1.5)) / effect.get('flip_seconds',.3))
                    im = im.rotate(-180 * turn, resample=Image.Resampling.NEAREST, fillcolor=self.theme.status_bg)
            return im
        im = Image.new('RGB', (12, 12), self.theme.status_bg)
        d = ImageDraw.Draw(im)
        color = self.theme.status_fg
        if kind == 'wake':
            effect = self.theme.animation('ANI-003')
            level = (.4 + .6 * (1 - math.cos(2 * math.pi * elapsed / effect.get('cycle',1.5))) / 2) if effect['kind'] == 'breath' else 1.
            rgb = Image.new('RGB', (1, 1), color).getpixel((0, 0))
            color = tuple(round(c * level) for c in rgb)
            d.ellipse((3, 3, 8, 8), outline=color)
            for line in [(5, 0, 5, 1), (5, 10, 5, 11), (0, 5, 1, 5), (10, 5, 11, 5)]:
                d.line(line, fill=color)
        elif kind == 'think':
            d.line([(2, 1), (9, 1), (8, 3), (4, 7), (2, 10), (9, 10), (8, 8), (4, 4), (2, 1)], fill=color)
            d.polygon([(4, 2), (7, 2), (5, 4)], fill=color)
            effect = self.theme.animation('ANI-001')
            phase = elapsed % effect.get('cycle',1.5)
            turn = min(1., phase / effect.get('flip_seconds',.3)) if effect['kind'] == 'flip' else 1.
            if turn < 1:
                im = im.rotate(-180 * turn, resample=Image.Resampling.NEAREST, fillcolor=self.theme.status_bg)
        elif kind == 'idle':
            d.ellipse((2, 2, 9, 9), outline=color)
        elif kind == 'mic':
            d.rounded_rectangle((4, 0, 7, 6), radius=1, outline=color)
            d.arc((2, 2, 9, 9), 0, 180, fill=color)
            d.line((5, 9, 5, 11), fill=color)
            d.line((3, 11, 8, 11), fill=color)
        elif kind == 'message':
            d.rectangle((1, 1, 10, 8), outline=color)
            d.line([(3, 8), (3, 11), (6, 8)], fill=color)
        elif kind == 'camera':
            d.rectangle((0, 3, 11, 10), outline=color)
            d.rectangle((3, 1, 7, 3), outline=color)
            d.ellipse((4, 5, 7, 8), outline=color)
        elif kind == 'tool':
            d.arc((0, 0, 6, 6), 50, 310, fill=color)
            d.line((4, 5, 10, 11), fill=color, width=2)
        elif kind == 'speak':
            d.polygon([(1, 4), (3, 4), (6, 1), (6, 10), (3, 7), (1, 7)], outline=color)
            d.arc((5, 1, 11, 10), -60, 60, fill=color)
        elif kind == 'error':
            d.line([(5, 0), (11, 10), (0, 10), (5, 0)], fill=color)
            d.line((5, 4, 5, 6), fill=color)
            d.point((5, 8), fill=color)
        elif kind == 'stop':
            d.rectangle((2, 2, 9, 9), outline=color, width=2)
        return im.resize((self.theme.icon_size, self.theme.icon_size), Image.Resampling.NEAREST)

    def render(self, scene: Scene, elapsed: float, typewriter=False):
        im = Image.new('RGB', (128, 128), '#000000')
        d = ImageDraw.Draw(im)
        t = self.theme
        if scene.role == 'blank':
            return im
        if scene.role == 'logo':
            if self.main.getlength(t.logo) > 120:
                raise ValueError('preview logo exceeds safe width')
            d.text((64, 64), t.logo, font=self.main, fill=t.main_fg, anchor='mm')
            return im
        d.rectangle((0, 0, 127, 19), fill=t.status_bg)
        d.rectangle((0, 21, 127, 127), fill=t.main_bg)
        d.line((0, 20, 127, 20), fill='#30343A')
        x = 4
        for kind in scene.icons:
            im.paste(self.icon(kind, elapsed), (x, 2 + (16 - t.icon_size) // 2))
            x += t.icon_size + t.icon_gap
        if x + self.status.getlength(scene.state) > 124:
            raise ValueError('status content exceeds safe width')
        d.text((x, 2 + (16 - t.status_line_height) // 2), scene.state,
               font=self.status, fill=t.status_fg, anchor='lt')
        font = self.error if scene.role == 'error' else self.main
        color = {'input': t.input_fg, 'reply': t.reply_fg, 'error': t.error_fg}.get(scene.role, t.main_fg)
        line_height = t.error_line_height if scene.role == 'error' else t.main_line_height
        lines = self.lines(scene.text, font, 100 // line_height) if scene.text else []
        count = sum(map(len, lines))
        visible = count
        effect = t.animation(scene.motion)
        if typewriter and effect['kind'] == 'typewriter' and elapsed < effect.get('max_seconds',3.):
            # Only synthetic fixture text; not a general grapheme-aware Core renderer.
            visible = min(count, int(elapsed / effect.get('char_seconds',.08)))
        area = Image.new('RGB', (120, 100), t.main_bg)
        ad = ImageDraw.Draw(area)
        for n, line in enumerate(lines):
            part = line[:visible]
            visible = max(0, visible - len(line))
            ad.text((0, n * line_height), part, font=font, fill=color, anchor='lt')
        im.paste(area, (4, 24))
        return im


def rgb565(im):
    data = bytearray()
    pixels = im.convert('RGB').tobytes()
    for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]):
        value = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        data.extend((value >> 8, value & 255))
    return bytes(data)


@dataclass
class Player:
    index: int = 0
    elapsed: float = 0.
    paused: bool = False
    typewriter: bool = False
    done: bool = False

    def command(self, command):
        if command in ('', 'n'):
            self.index = min(self.index + 1, len(SCENES) - 1)
            self.elapsed = 0.
        elif command == 'b':
            self.index = max(0, self.index - 1)
            self.elapsed = 0.
        elif command == 'r':
            self.elapsed = 0.
        elif command == 'p':
            self.paused = not self.paused
        elif command == 't':
            self.typewriter = not self.typewriter
            self.elapsed = 0.
        elif command == 'q':
            self.done = True


async def play(device, renderer, *, interactive=False, seconds=4., fps=10, max_seconds=120.,
               typewriter=False, controls=None):
    player = controls or Player(typewriter=typewriter)
    loop = asyncio.get_running_loop()
    reader = False
    installed_signals = []
    started = False
    session_start = time.monotonic()
    previous_tick = session_start
    last = None
    announced = None
    try:
        if interactive:
            def read_command():
                line = sys.stdin.readline()
                player.command(line.strip().lower() if line else 'q')
            loop.add_reader(sys.stdin.fileno(), read_command)
            reader = True
        for signum in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signum, lambda: player.command('q'))
            installed_signals.append(signum)
        await device.start()
        started = True
        if device.size() != (128, 128):
            raise ValueError('review requires 128x128 device')
        while not player.done and time.monotonic() - session_start < max_seconds:
            now = time.monotonic()
            scene = SCENES[player.index]
            if announced != player.index:
                print(f'{player.index + 1:02}/{len(SCENES)} {scene.key}: {scene.label}', flush=True)
                announced = player.index
            frame = rgb565(renderer.render(scene, player.elapsed, player.typewriter))
            if frame != last:
                device.write_pixels(frame)
                device.show()
                last = frame
            if not player.paused:
                player.elapsed += now - previous_tick
            previous_tick = now
            if not interactive and player.elapsed >= seconds:
                if player.index == len(SCENES) - 1:
                    break
                player.command('n')
            await asyncio.sleep(1 / fps)  # No catch-up queue if SPI is slow.
    finally:
        if reader:
            loop.remove_reader(sys.stdin.fileno())
        for signum in installed_signals:
            loop.remove_signal_handler(signum)
        try:
            if started:
                try:
                    device.clear()
                    device.show()
                except Exception:
                    print('Final blank failed; continuing device cleanup.', file=sys.stderr)
        finally:
            await device.stop()


def export(renderer, directory, typewriter):
    directory.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (768, math.ceil(len(SCENES) / 3) * 304), '#202328')
    sd = ImageDraw.Draw(sheet)
    for index, scene in enumerate(SCENES):
        name = scene.key.replace('/', '_')
        still = renderer.render(scene, 1., False)
        still.save(directory / f'{name}.png')
        frames = [renderer.render(scene, n / 10, typewriter) for n in range(30)]
        frames[0].save(directory / f'{name}.gif', save_all=True, append_images=frames[1:], duration=100,
                       loop=0, disposal=2)
        x, y = (index % 3) * 256, (index // 3) * 304
        sd.text((x + 8, y + 4), scene.key, font=renderer.main, fill='white')
        sheet.paste(still.resize((256, 256), Image.Resampling.NEAREST), (x, y + 28))
    sheet.save(directory / 'overview.png')
    entries = [{'key': s.key, 'label': s.label, 'file': s.key.replace('/', '_')} for s in SCENES]
    html = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<title>M7 Display review</title><style>
body{background:#202328;color:#fff;font:16px system-ui;margin:24px;max-width:900px}
img{width:384px;height:384px;image-rendering:pixelated;display:block;margin:20px 0}
button,select{font:inherit;padding:8px;margin:4px}p{line-height:1.6}
</style><h1 id="theme-label">工作站動態 review</h1>
<p>合成內容；標誌、輸入色與動畫速度為暫定預覽。這不是 Pi／OLED 或 Core 整合證據。</p>
<select id="scenes"></select><h2 id="label"></h2><img id="frame" alt="128×128 畫面預覽">
<button onclick="move(-1)">上一張</button><button onclick="move(1)">下一張</button>
<button onclick="show()">重播動畫</button><button id="auto" onclick="toggleAuto()">自動輪播</button>
<p>原圖 128×128，放大三倍。左右鍵切換；每張 GIF 為約三秒的設計預覽。動畫使用本次 export 的打字機選項。</p>
<p><a href="overview.png" style="color:#70cfff">所有畫面靜態總覽</a></p>
<script>const data=__SCENES__;const theme=__THEME__;document.getElementById('theme-label').textContent=theme+' · 工作站動態 review';let index=0,timer=null;
const sel=document.getElementById('scenes');data.forEach((s,i)=>{let o=document.createElement('option');
o.value=i;o.textContent=s.key+' '+s.label;sel.append(o)});
function show(){sel.value=index;document.getElementById('label').textContent=data[index].key+' · '+data[index].label;
document.getElementById('frame').src=data[index].file+'.gif?replay='+Date.now()}
function move(step){index=Math.max(0,Math.min(data.length-1,index+step));show()}
function toggleAuto(){if(timer){clearInterval(timer);timer=null}else{timer=setInterval(()=>{
if(index===data.length-1){toggleAuto();return}move(1)},4000)}
document.getElementById('auto').textContent=timer?'停止輪播':'自動輪播'}
sel.onchange=()=>{index=Number(sel.value);show()};document.addEventListener('keydown',e=>{
if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1)});show();</script></html>'''
    theme_json = json.dumps(renderer.theme.theme_id).replace('<', '\\u003c')
    (directory / 'index.html').write_text(html.replace('__SCENES__', json.dumps(entries)).replace('__THEME__', theme_json), encoding='utf-8')
    print(f'Exported {len(SCENES)} stills and GIF previews (synthetic, unverified on OLED).')


def hardware_preflight(config):
    load_display_config(config)
    data = json.loads(Path(config).read_text())
    model = Path('/proc/device-tree/model')
    if not model.exists() or not model.read_text().startswith('Raspberry Pi 5'):
        raise RuntimeError('real review requires Raspberry Pi 5')
    result = subprocess.run(['fuser', data['spi']['device']], capture_output=True)
    if result.returncode != 1:
        raise RuntimeError('SPI owner present or owner check failed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend', choices=('mock', 'ssd1351'), default='mock')
    p.add_argument('--theme', type=Path, default=REVIEW_DIR / 'themes/THM-baseline.json', help='theme JSON; shared scenes/player remain unchanged')
    p.add_argument('--font-dir', type=Path, help='offline Noto Sans TC Regular/Medium font directory')
    p.add_argument('--config', type=Path, help='recorded local SSD1351 JSON fixture config')
    p.add_argument('--so', type=Path, help='existing Pi-built libdisplay.so')
    p.add_argument('--interactive', action='store_true', help='terminal commands with Enter; automatic otherwise')
    p.add_argument('--seconds', type=float, default=4., help='automatic dwell per screen')
    p.add_argument('--fps', type=int, default=10, help='review frame ceiling; not a product budget')
    p.add_argument('--max-seconds', type=float, default=120., help='hard session limit, including pause')
    p.add_argument('--typewriter', action='store_true', help='enable synthetic Speak reveal preview')
    p.add_argument('--input-color', default=None, help='provisional input color')
    p.add_argument('--reply-color', default=None, help='provisional reply color')
    p.add_argument('--logo-text', default=None, help='placeholder pending logo design')
    p.add_argument('--export', type=Path, help='export PNG/GIF previews without opening a device')
    p.add_argument('--capture', type=Path, help='mock-only raw RGB565-decoded frame PNG directory')
    p.add_argument('--list', action='store_true')
    args = p.parse_args()
    if args.list:
        for s in SCENES:
            print(f'{s.key}: {s.label}')
        return 0
    if not args.font_dir:
        p.error('--font-dir is required')
    if not (0.1 <= args.seconds <= 30 and 1 <= args.fps <= 15 and 1 <= args.max_seconds <= 300):
        p.error('seconds must be 0.1..30, fps 1..15, max-seconds 1..300')
    if args.interactive and not sys.stdin.isatty():
        p.error('--interactive requires a terminal; use automatic mode for noninteractive SSH')
    from dataclasses import replace
    theme = load_theme(args.theme)
    overrides = {k:v for k,v in {'input_fg':args.input_color,'reply_fg':args.reply_color,'logo':args.logo_text}.items() if v is not None}
    theme = replace(theme, **overrides)
    renderer = Renderer(args.font_dir, theme)
    # Validate every fixture before opening any physical hardware.
    for scene in SCENES:
        renderer.render(scene, 0., False)
    if args.export:
        export(renderer, args.export, args.typewriter)
        return 0
    if args.backend == 'ssd1351' and (not args.config or not args.so):
        p.error('ssd1351 requires --config and --so')
    if args.backend == 'ssd1351' and args.capture:
        p.error('--capture is mock-only; use --export for design previews')
    print(f'{theme.theme_id} review: placeholder logo/colors/timing; not Core integration evidence.', flush=True)
    if args.interactive:
        print('Commands + Enter: n/Enter next, b previous, p pause, r replay, t typewriter, q quit.')
    if args.capture:
        args.capture.mkdir(parents=True, exist_ok=True)
    # Prevent two review players from owning the fixture; never kill other owners.
    with open(Path(tempfile.gettempdir()) / 'snowboard-m7-review.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.backend == 'ssd1351':
            hardware_preflight(args.config)
        device = create_device('waveshare_oled_1in5_rgb', mock=args.backend == 'mock',
                               config_path=args.config, so_path=args.so, save_frames_to=args.capture)
        asyncio.run(play(device, renderer, interactive=args.interactive, seconds=args.seconds,
                         fps=args.fps, max_seconds=args.max_seconds, typewriter=args.typewriter))
    print('Review ended; device released.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        # Keep private fixture/host paths out of terminal summaries.
        print(f'Review failed ({type(exc).__name__}); check local dependencies/configuration.', file=sys.stderr)
        raise SystemExit(1)
