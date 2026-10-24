# M3-AUDI-001 Hardware Test Card

- Status: Pass
- Product revision: HEAD / cab627705c341d0058e0c395e96d0be10c4c4239
- Hardware and wiring: hardware_and_wiring in `results/M3-AUDI-001.json`
- Artifact / config / fixture identity: `results/M3-AUDI-001.json`
- Command: `/home/yee/workspace/snowboard-agent/.venv/bin/python -m pytest -p no:cacheprovider -m rpi -q tests/test_m3_btn_001_002_003_004_005_rpi.py::test_m3_btn_001 tests/test_m3_btn_001_002_003_004_005_rpi.py::test_m3_btn_002 tests/test_m3_btn_001_002_003_004_005_rpi.py::test_m3_btn_003 tests/test_m3_btn_001_002_003_004_005_rpi.py::test_m3_btn_004 tests/test_m3_btn_001_002_003_004_005_rpi.py::test_m3_btn_005 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_001 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_002 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_003 tests/test_m3_audi_001_002_003_004_rpi.py::test_m3_audi_004 tests/test_m3_cami_001_002_003_rpi.py::test_m3_cami_001 tests/test_m3_cami_001_002_003_rpi.py::test_m3_cami_002 tests/test_m3_cami_001_002_003_rpi.py::test_m3_cami_003 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_001 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_002 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_003 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_004 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_005 tests/test_m3_dspi_001_002_003_004_005_006_rpi.py::test_m3_dspi_006 tests/test_m3_gpioi_001_002_rpi.py::test_m3_gpioi_001 tests/test_m3_gpioi_001_002_rpi.py::test_m3_gpioi_002`
- Expected: direct hw: native 48k stereo S32_LE opens; capture yields 640-byte frames; playback fully consumes native PCM
- Actual: 3/3 capture frames exact; one 960-frame playback fixture completed without short-write error
- Started / finished (UTC): 2026-08-17T00:45:02.024162+00:00 / 2026-08-17T00:45:02.204897+00:00
- Exit code: 0 (written only after all card assertions pass)
- Result / log / media index: `results/M3-AUDI-001.json`, `logs/`, `media-metadata/`
