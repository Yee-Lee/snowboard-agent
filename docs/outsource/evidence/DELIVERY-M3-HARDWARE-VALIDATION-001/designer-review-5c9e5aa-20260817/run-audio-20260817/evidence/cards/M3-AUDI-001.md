# M3-AUDI-001 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-AUDI-001.json`
- Artifact / config / fixture identity: `results/M3-AUDI-001.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_001 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_002 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_004`
- Expected: direct hw: native 48k stereo S32_LE opens; capture yields 640-byte frames; playback fully consumes native PCM
- Actual: 3/3 capture frames exact; one 960-frame playback fixture completed without short-write error
- Started / finished (UTC): 2026-08-17T14:29:10.826345+00:00 / 2026-08-17T14:29:11.224144+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-AUDI-001.json`, `logs/`, `media-metadata/`
