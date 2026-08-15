#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd); cd "$root"
export PYTHONPATH="$root/poc_audio/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m audio_poc.fixture_delivery "$@"
