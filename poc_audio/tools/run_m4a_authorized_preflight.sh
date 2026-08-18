#!/usr/bin/env bash
# Verify ACK-authorized candidate artifacts without importing candidate runtimes.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 --artifact-dir DIR --output FILE [--candidate ID]..." >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_authorized_preflight \
  --source-sha "$source_sha" "$@"
