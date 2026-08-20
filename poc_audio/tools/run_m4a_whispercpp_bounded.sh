#!/usr/bin/env bash
# Run review-only VAD-label-bounded Q8 screening; never captures or plays audio.
set -euo pipefail

if [[ $# -lt 18 ]]; then
  echo "usage: $0 --artifact-dir DIR --fixture-dir DIR --vad-label-index FILE --binary FILE --build-report FILE --work-dir DIR --output FILE --mode screening|diagnostic --threads 1|2|4 [--hot-repetitions 1|2]" >&2
  exit 2
fi

if [[ "${AUDIO_POC_OFFLINE_NETNS_ACTIVE:-}" != "1" ]]; then
  exec 9</proc/self/ns/net
  export AUDIO_POC_CALLER_NETNS_FD=9
  export AUDIO_POC_OFFLINE_NETNS_ACTIVE=1
  exec unshare --user --map-root-user --net -- bash "$0" "$@"
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "refusing bounded screening from a dirty POC worktree" >&2
  exit 1
fi
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_whispercpp_bounded \
  --source-sha "$source_sha" "$@"
