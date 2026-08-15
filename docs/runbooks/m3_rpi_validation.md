# M3 Raspberry Pi validation runbook

This runbook is for the exact Core candidate SHA after USER approves a
candidate commit.  It is diagnostic and evidence preparation; Core Tester
remains responsible for independent acceptance.

## Preconditions

1. Check out the full 40-character candidate SHA on the Pi 5.
2. Build the selected display artifact and install the selected Audio Option A
   packages through the target clean-build flow.  Do not place wheels, `.so`,
   raw PCM, or private config in Core Git.
3. Copy `config.example.yaml` to a sanitized Pi-local config and set the real
   audio, display, camera, and GPIO values.  Create a candidate-specific
   evidence directory from `docs/outsource/evidence/M3-developer-template/`.
4. With power off, confirm the OLED, CSI, I2S, button, and safe GPIO output
   wiring.  Never hot-unplug powered SPI, CSI, GPIO, or I2S hardware.

## Environment

Set only sanitized local paths and manual observations:

```bash
export SBD_M3_RPI_CONFIG=/protected/path/config.m3.local.yaml
export SBD_M3_EVIDENCE_DIR=/protected/path/evidence/results
export SBD_M3_INTERACTION_TIMEOUT_SECONDS=30
export SBD_M3_GPIO_OUTPUT_PIN=17  # only a USER-confirmed safe pin/load
```

Manual observations are explicit PASS/FAIL inputs.  Do not set them until the
USER has observed the named fixture:

```bash
export SBD_M3_MANUAL_M3_AUDI_003=PASS
export SBD_M3_MANUAL_M3_DSPI_002=PASS
export SBD_M3_MANUAL_M3_DSPI_005=PASS
export SBD_M3_MANUAL_M3_GPIOI_002=PASS
export SBD_M3_MANUAL_M3_BTN_002=PASS
export SBD_M3_MANUAL_M3_BTN_004=PASS
export SBD_M3_MANUAL_M3_BTN_005=PASS
```

## Run cards in hardware sessions

Run each group separately so one wiring or observation failure is isolated:

```bash
python -m pytest -v -m rpi tests/test_m3_audi_001_002_003_004_rpi.py
python -m pytest -v -m rpi tests/test_m3_cami_001_002_003_rpi.py
python -m pytest -v -m rpi tests/test_m3_gpioi_001_002_rpi.py tests/test_m3_btn_001_002_003_004_005_rpi.py
python -m pytest -v -m rpi tests/test_m3_dspi_001_002_003_004_005_006_rpi.py
```

Each successful card writes a sanitized JSON result to
`$SBD_M3_EVIDENCE_DIR`.  Complete a copy of `CARD_TEMPLATE.md` for each card
with exact SHA, configuration/artifact/fixture checksums, command, timestamps,
and USER observation.  A test failure or manual `FAIL` remains a failure; do
not overwrite it in a card.

After configuring the target environment, Tester may run the milestone gate:

```bash
python -m pytest -v -m rpi tests/milestones/test_m3_rpi_hal.py
```

The cards are executable but are not recorded as `Pass` until the target run
and its candidate-SHA evidence have both completed.  Missing local config,
hardware, evidence directory, or manual observation fails the relevant card.
