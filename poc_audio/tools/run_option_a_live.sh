#!/usr/bin/env bash
# Run P4-A06 through P4-A09 with direct ALSA capture and native-silence playback.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"
export PYTHONPATH="$repo_root/poc_audio/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m audio_poc.option_a_live "$@"
