# M3-GPIOI-001 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-GPIOI-001.json`
- Artifact / config / fixture identity: `results/M3-GPIOI-001.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_gpioi_001_002_rpi.py::test_m3_gpioi_001`
- Expected: loopback edge, kernel debounce, idempotent unregister, and output level all work
- Actual: events=[('rising', 1377.212009193), ('falling', 1377.268013571), ('rising', 1377.392011484)]; fast edge suppressed
- Started / finished (UTC): 2026-08-17T14:41:49.078097+00:00 / 2026-08-17T14:41:49.434913+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-GPIOI-001.json`, `logs/`, `media-metadata/`
