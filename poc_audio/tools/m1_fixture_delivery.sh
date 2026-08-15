#!/usr/bin/env bash
# Prepare immutable M1 native fixtures in the Core-selected delivery PCM format.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$root"

python_bin="${PYTHON_BIN:-}"
if [[ -z "$python_bin" ]]; then
  if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    python_bin="$VIRTUAL_ENV/bin/python"
  elif [[ -x "$root/poc_audio/evidence/m3_option_a/20260815T-a10-rerun2-de3b0ba/raw/a10-clean-build/rerun-env/bin/python" ]]; then
    python_bin="$root/poc_audio/evidence/m3_option_a/20260815T-a10-rerun2-de3b0ba/raw/a10-clean-build/rerun-env/bin/python"
  elif [[ -x "$root/.venv/bin/python" ]]; then
    python_bin="$root/.venv/bin/python"
  elif [[ -x "/Users/yee/Workspace/snowboard-agent/.venv/bin/python" ]]; then
    python_bin="/Users/yee/Workspace/snowboard-agent/.venv/bin/python"
  else
    python_bin="python3"
  fi
fi

if ! "$python_bin" -c "import samplerate" >/dev/null 2>&1; then
  echo "Error: $python_bin does not have 'samplerate' installed. Please specify PYTHON_BIN pointing to a verified runtime." >&2
  exit 1
fi

export PYTHONPATH="$root/poc_audio/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$python_bin" -m audio_poc.fixture_delivery "$@"
