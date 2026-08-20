#!/usr/bin/env bash
# Run frozen ACK-002 ASR qualification with no capture, playback, or transcript output.
set -euo pipefail

if [[ $# -lt 12 ]]; then
  echo "usage: $0 --artifact-dir DIR --fixture-dir DIR --binary FILE --build-report FILE --work-dir DIR --output FILE [--candidate ID] [--q8-result FILE]" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "refusing qualification from a dirty POC worktree" >&2
  exit 1
fi
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_whispercpp_qualification \
  --source-sha "$source_sha" "$@"
