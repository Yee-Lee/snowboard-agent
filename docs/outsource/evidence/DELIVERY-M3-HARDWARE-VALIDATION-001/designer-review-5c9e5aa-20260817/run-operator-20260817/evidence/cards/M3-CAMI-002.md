# M3-CAMI-002 Hardware Test Card

- Status: Pass
- Product revision: HEAD / 5c9e5aac47e7f4f0dd168d8c75541438ee74f858
- Hardware and wiring: hardware_and_wiring in `results/M3-CAMI-002.json`
- Artifact / config / fixture identity: `results/M3-CAMI-002.json`
- Command: `<repo-root>/.venv/bin/python -m pytest -vv -s -p no:cacheprovider -m rpi tests/test_m3_cami_001_002_003_rpi.py tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_001 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_003 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_004 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_006 tests/test_m3_gpioi_001_002_rpi.py`
- Expected: ResourceManager real-to-null fallback, camera=False, warning, app continues
- Actual: NullCamera owned by RM; capability false; startup and shutdown completed
- Started / finished (UTC): 2026-08-17T14:41:02.706218+00:00 / 2026-08-17T14:41:02.737487+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-CAMI-002.json`, `logs/`, `media-metadata/`
