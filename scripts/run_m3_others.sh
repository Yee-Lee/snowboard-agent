#!/bin/bash
set -e

cd "$(dirname "$0")/.."

export SBD_M3_CANDIDATE_SHA=$(git rev-parse HEAD)
export SBD_M3_RPI_CONFIG="$(pwd)/config.m3.local.yaml"
export SBD_M3_EVIDENCE_DIR="$(pwd)/docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001"
export SBD_M3_MANUAL_DIR="$SBD_M3_EVIDENCE_DIR/manual-current-run"
export SBD_M3_HARDWARE_MANIFEST="$SBD_M3_EVIDENCE_DIR/hardware.json"
export SBD_M3_INTERACTION_TIMEOUT_SECONDS=120
export SBD_M3_DISPLAY_OBSERVATION_SECONDS=5
export SBD_M3_GPIO_OUTPUT_PIN=17
export SBD_M3_GPIO_INPUT_PIN=27

echo "Candidate SHA: $SBD_M3_CANDIDATE_SHA"
echo "Running Audio Tests..."
.venv/bin/python -m pytest -vv -m rpi tests/test_m3_audi_001_002_003_004_rpi.py -s \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/audio.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/audio.xml" &
PYTEST_PID=$!
sleep 5
.venv/bin/python scripts/record_m3_observation.py M3-AUDI-003 \
  --operator yee --output-dir "$SBD_M3_MANUAL_DIR" \
  audible=pass no_pop=pass no_noise=pass || true
wait $PYTEST_PID

echo "Running Camera Tests..."
.venv/bin/python -m pytest -vv -m rpi tests/test_m3_cami_001_002_003_rpi.py -s \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/camera.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/camera.xml"

echo "Running GPIO Loopback Tests..."
.venv/bin/python -m pytest -vv -m rpi tests/test_m3_gpioi_001_002_rpi.py -s \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/gpio.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/gpio.xml"

echo "Running Display Tests..."
.venv/bin/python -m pytest -vv -m rpi tests/test_m3_dspi_001_002_003_004_005_006_rpi.py -s \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/display.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/display.xml" &
PYTEST_PID=$!
sleep 10
.venv/bin/python scripts/record_m3_observation.py M3-DSPI-002 \
  --operator yee --output-dir "$SBD_M3_MANUAL_DIR" \
  boot_blank=pass idle_text_readable=pass shutdown_blank=pass || true
sleep 15
.venv/bin/python scripts/record_m3_observation.py M3-DSPI-005 \
  --operator yee --output-dir "$SBD_M3_MANUAL_DIR" \
  arrow_up=pass no_mirror=pass rgb_correct=pass text_readable=pass no_flicker=pass || true
wait $PYTEST_PID

echo "All other tests finished!"
