#!/usr/bin/env bash
# Controlled local acquisition for the M1 authorized fixture plan.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"
export PYTHONPATH="$repo_root/poc_audio/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m audio_poc.fixture_recorder "$@"
