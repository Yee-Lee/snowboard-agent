# M3-DSPI-002 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-DSPI-002.json`
- Artifact / config / fixture identity: `results/M3-DSPI-002.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_002`
- Expected: boot blank, IDLE state text, and shutdown blank execute through lifecycle owner
- Actual: lifecycle rendered 5 presents; current-run checklist passed
- Started / finished (UTC): 2026-08-17T14:39:15.733120+00:00 / 2026-08-17T14:39:48.460428+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-DSPI-002.json`, `logs/`, `media-metadata/`
