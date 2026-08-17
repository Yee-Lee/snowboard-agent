# M3-AUDI-002 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-AUDI-002.json`
- Artifact / config / fixture identity: `results/M3-AUDI-002.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_001 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_002 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_004`
- Expected: missing ALSA input falls back through RM, audio=False, warning, app continues
- Actual: RM owns NullAudioInput; capability false; warning names device; startup/shutdown completed
- Started / finished (UTC): 2026-08-17T14:29:11.245123+00:00 / 2026-08-17T14:29:11.274961+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-AUDI-002.json`, `logs/`, `media-metadata/`
