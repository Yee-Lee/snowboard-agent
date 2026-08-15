#!/usr/bin/env bash
# Run locally on the Pi; reviews proposals without modifying immutable raw WAV files.
set -euo pipefail
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"
export PYTHONPATH="$repo_root/poc_audio/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m audio_poc.fixture_label_review "$@"
