# M3-AUDI-003 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-AUDI-003.json`
- Artifact / config / fixture identity: `results/M3-AUDI-003.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_003`
- Expected: fixed 440 Hz fixture is audible without obvious pop or noise
- Actual: AudioOutput.play completed; current-run operator checklist passed
- Started / finished (UTC): 2026-08-17T14:33:04.556647+00:00 / 2026-08-17T14:33:50.065656+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-AUDI-003.json`, `logs/`, `media-metadata/`
