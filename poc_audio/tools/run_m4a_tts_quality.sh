#!/usr/bin/env bash
# Generate the ten controlled Matcha risk-review WAVs; never opens playback.
set -euo pipefail

if [[ $# -lt 6 ]]; then
  echo "usage: $0 --artifact-dir DIR --work-dir DIR --output-dir DIR" >&2
  exit 2
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || {
  echo "Matcha quality generation requires a clean Git worktree" >&2
  exit 1
}
runtime_python="${M4A_RUNTIME_DIR:?M4A_RUNTIME_DIR is required}/bin/python"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PIP_NO_INDEX=1 \
PYTHONPATH="$repo_root/poc_audio/src" "$runtime_python" -m audio_poc.m4a_tts_quality \
  --source-sha "$source_sha" "$@"
