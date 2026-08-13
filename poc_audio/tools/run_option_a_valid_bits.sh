#!/usr/bin/env bash
# Analyze authorized native Pilot WAVs without emitting audio samples.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)

export PYTHONPATH="$repo_root/poc_audio/src"
exec python3 -m audio_poc.option_a_valid_bits "$@"
