#!/usr/bin/env bash
# Run one exact M2A row offline; never captures or plays audio.
set -euo pipefail

if [[ "${AUDIO_POC_OFFLINE_NETNS_ACTIVE:-}" != "1" ]]; then
  exec 9</proc/self/ns/net
  export AUDIO_POC_CALLER_NETNS_FD=9
  export AUDIO_POC_OFFLINE_NETNS_ACTIVE=1
  exec unshare --user --map-root-user --net -- bash "$0" "$@"
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "refusing M2A survey from a dirty POC worktree" >&2
  exit 1
fi
export PYTHONPATH="$repo_root/poc_audio/src"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PIP_NO_INDEX=1
python3 -m audio_poc.m2a_survey "$@"
