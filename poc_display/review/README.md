# Reusable Display theme review

This is the common review entrypoint for subsequent theme work. It runs offline, uses synthetic fixtures,
and shares one raster renderer between workstation exports, the existing MockDisplayDevice and the SSD1351 HAL.
It is Display POC tooling, not proof of Core Presenter/Arbiter integration or product acceptance.

## Authoring contract

- Design hierarchy remains Style → Theme → Scene. This first implementation reviews the icon + text tool
  style; it does not implement a user-facing Style switch or certify every style.
- `themes/THM-baseline.json`: theme identity, independent StatusBar/Main colors and typography, icon dimensions,
  logo placeholder and theme-owned animation descriptions. Input/reply colors and preview timing are provisional.
- `scenes.json`: shared synthetic fixtures for SCN-01–SCN-09, including empty/text/multi-source Perception,
  idle protection and final shutdown Blank. These are illustrative snapshots, not simulated Core events.
- ANI identities are stable across themes: ANI-001 thinking hourglass, ANI-002 boot logo, ANI-003 preparation
  rays, ANI-004 shutdown logo. ANI-005 reserves gradual text reveal for the review tool; it is not selected as
  the default product treatment.
- Animation entries start with a `description`. Their `preview` settings are implementation choices needed
  to demonstrate them, not a requirement to parameterize every future effect or freeze product timing.
- Supported preview behaviors today: static, hourglass flip, preparation brightness breathing and optional
  Speak typewriter. A new effect requires extending Renderer and behavioral tests; JSON alone cannot define
  arbitrary animation. Keep the semantic ANI ID when redesigning that item for another theme.
- `icon_files` may map a role (`idle`, `wake`, `mic`, `message`, `camera`, `think`, `tool`, `speak`, `error`)
  or `stop` to a PNG relative to the theme file. Icons must match `icon_size`; RGBA is supported. Absent entries use
  procedural draft icons. Retained assets need source/license metadata before delivery; do not use private media.
- To create a theme, copy THM-baseline.json, give it a new `theme_id`, then change its visual settings and
  animation descriptions. Keep shared scene keys and fixture meaning unchanged when comparing themes.
- Black canvas/backgrounds, 128×128 profile, 20 px StatusBar and safe rectangles are retained constraints.
  Changed typography is an exploration delta for Core to review. Status overflow fails rather than silently
  shrinking content. Main capacity is recomputed from the selected line height.

## Workstation review

Requirements: Python 3.10+, Pillow, this repository's HAL, offline Noto Sans TC Regular/Medium OTFs.
Observed workstation versions: Pillow 12.3.0, pytest 9.1.1. No assets are downloaded at runtime.
Set `M7_FONT_DIR` to the local offline font directory; do not put private paths into Git.

```sh
python3 poc_display/tools/m7_review.py --list
python3 poc_display/tools/m7_review.py --theme poc_display/review/themes/THM-baseline.json --font-dir "$M7_FONT_DIR" --export /tmp/m7-theme-review --typewriter
open /tmp/m7-theme-review/index.html
```

The local browser page shows GIF animations, previous/next/replay controls and optional automatic rotation;
it needs no web server/network. `overview.png` gives all stills. Per-scene PNG/GIFs stay in the requested
external output directory. The page's automatic rotation changes scenes; it is not a performance measurement.

Run the actual player against the mock HAL, optionally saving every transmitted RGB565-decoded frame:

```sh
python3 poc_display/tools/m7_review.py --font-dir "$M7_FONT_DIR" --backend mock --typewriter --capture /tmp/m7-review-frames
python3 poc_display/tools/m7_review.py --font-dir "$M7_FONT_DIR" --backend mock --interactive
M7_REVIEW_FONT_DIR="$M7_FONT_DIR" python3 -m pytest poc_display/tests/test_m7_review.py -q
```

## Pi / physical OLED review

Use the existing recorded SSD1351 fixture JSON, Pi-built native library and offline font directory. Check
DC/RST owners using the established fixture preflight; ensure other Display processes are stopped normally.
Do not kill another owner or modify fixture wiring/configuration for this tool. The player checks Pi 5 identity,
strict config, SPI ownership and a local review lock before opening. The native driver still owns GPIO claims.

```sh
python3 poc_display/tools/m7_review.py --backend ssd1351 --config "$M7_DISPLAY_CONFIG" --so "$M7_DISPLAY_SO" --font-dir "$M7_FONT_DIR" --interactive --typewriter
```

Terminal commands require Enter: `n` or empty line next, `b` previous, `p` freeze/resume both animation
and elapsed review time, `r` restart current effect, `t` toggle/restart Speak typewriter, `q` exit.
Use an allocated SSH terminal for `--interactive`. Without it, the default is one automatic pass, 4 seconds
per screen, at most 10 frames/s; `--seconds`/`--fps` can change review pacing within bounded ranges.

- Hard session limit is 120 seconds by default, including pauses; `--max-seconds` accepts 1–300 seconds.
- No infinite playlist or catch-up queue. Static duplicate frames do not trigger another SPI flush.
- Exit, SIGINT/SIGTERM, cancellation or error attempts a final black frame and always calls device stop.
  If rendering/presentation is broken, black cannot be guaranteed; cleanup is still attempted.
- Logo, idle blank and interrupt are review fixtures; their dwell times do not represent production lifecycle
  delays. Multiple input icons are synthetic, not proof that Core supplies the active-module set.
- Current typewriter slices only the synthetic fixtures. General grapheme-aware production reveal is still
  needed before applying it to arbitrary text. Missing glyphs and full privacy/stale handling remain Core contracts.

## Repeatable verification boundary

For each retained theme/code candidate: run host behavior checks, export and review static/motion examples,
then run the same bytes on Pi/OLED, including next/previous/pause/replay/typewriter/quit, SIGINT cleanup and
post-run SPI/GPIO owner checks. Record human readability, flicker and smoothness separately from automatic
results. Identify exact code/theme/assets at this deliberate transfer boundary; do not add digest checks to
normal player startup. Keep raw captures, GIFs and logs in external custody or ignored M7 evidence directories.

Review feedback found the baseline「回應中」+「已中止」combination confusing. The revised review fixture
uses a stop icon +「中止中」during accepted interruption. This is a proposed display projection, not a new
State Manager state; Core must review the minimal ownership/hint delta before production adoption.
Input/reply preview colors are now white/pale green, respectively; these remain preview values pending theme selection.

Current status: workstation checks completed; the first same-bytes Pi/OLED pass succeeded, with a follow-up
pass for the two review fixes recorded in the M7 review evidence summary.
This tool enables repeatable review; it does not replace product-load measurements or Core acceptance tests.
