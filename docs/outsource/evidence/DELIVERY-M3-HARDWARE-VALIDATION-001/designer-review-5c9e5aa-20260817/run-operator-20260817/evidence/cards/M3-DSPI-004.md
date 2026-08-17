# M3-DSPI-004 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-DSPI-004.json`
- Artifact / config / fixture identity: `results/M3-DSPI-004.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_cami_001_002_003_rpi.py tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_001 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_003 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_004 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_006 tests/test_m3_gpioi_001_002_rpi.py`
- Expected: two arbiter write_main cycles reopen; each stop closes handle/GPIO/SPI/thread; stop idempotent
- Actual: cycles=[{'cycle': 1, 'handle': 0, 'fds': []}, {'cycle': 2, 'handle': 0, 'fds': []}]; residual_threads=[]
- Started / finished (UTC): 2026-08-17T14:41:05.192095+00:00 / 2026-08-17T14:41:06.835344+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-DSPI-004.json`, `logs/`, `media-metadata/`
