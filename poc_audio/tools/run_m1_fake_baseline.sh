#!/usr/bin/env bash
# Run the deterministic M1 fake baseline without installing third-party code.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)

export PYTHONPATH="$repo_root/poc_audio/src"
exec python3 -m audio_poc.run_fake_baseline "$@"
