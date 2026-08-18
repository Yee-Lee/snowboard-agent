#!/usr/bin/env bash
# One frozen ASR fixture plus one tracked TTS prompt; never opens playback.
set -euo pipefail

if [[ $# -lt 10 ]]; then
  echo "usage: $0 --artifact-dir DIR --runtime-dir DIR --fixture-dir DIR --work-dir DIR --output FILE" >&2
  exit 2
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || {
  echo "candidate smoke requires a clean Git worktree" >&2
  exit 1
}
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_candidate_smoke \
  --source-sha "$source_sha" "$@"
