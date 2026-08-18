#!/usr/bin/env bash
# Offline install/import identity check for the two focused Gate 1B rows.
set -euo pipefail

if [[ $# -lt 6 ]]; then
  echo "usage: $0 --artifact-dir DIR --runtime-dir DIR --output FILE" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || {
  echo "runtime preflight requires a clean Git worktree" >&2
  exit 1
}
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_runtime_preflight \
  --source-sha "$source_sha" "$@"
