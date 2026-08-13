#!/usr/bin/env bash
# Prepare or validate an M1 P4 Option A evidence packet.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)

export PYTHONPATH="$repo_root/poc_audio/src"
exec python3 -m audio_poc.option_a_validation "$@"
