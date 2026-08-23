#!/usr/bin/env bash
# Matcha P12 inference inside an unprivileged network namespace; no playback.
set -euo pipefail

if [[ $# -lt 8 ]]; then
  echo "usage: $0 --artifact-dir DIR --runtime-dir DIR --work-dir DIR --output FILE" >&2
  exit 2
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || {
  echo "Matcha offline test requires a clean Git worktree" >&2
  exit 1
}
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_tts_offline \
  --source-sha "$source_sha" "$@"
