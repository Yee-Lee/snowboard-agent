#!/usr/bin/env bash
# Run deterministic P4-A03 through A05 conversion validation.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)

export PYTHONPATH="$repo_root/poc_audio/src"
exec python3 -m audio_poc.run_option_a_conversion "$@"
