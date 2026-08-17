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

echo "====================================================="
echo "Candidate SHA: $SBD_M3_CANDIDATE_SHA"
echo "Starting Button tests..."
echo "Please follow the prompts to press the button!"
echo "====================================================="

.venv/bin/python -m pytest -vv -m rpi tests/test_m3_btn_001_002_003_004_005_rpi.py -s \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/button.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/button.xml"

echo "Button tests finished successfully!"
