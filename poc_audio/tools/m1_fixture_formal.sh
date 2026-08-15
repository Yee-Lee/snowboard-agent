#!/usr/bin/env bash
# Run or verify the Formal completion in the reviewed Pilot fixture revision.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"

usage() {
  printf '%s\n' \
    'usage: m1_fixture_formal.sh {record|verify|list}' \
    'Run this command locally on the Pi in an attached terminal.'
}

mode=${1:-record}
[[ $# -le 1 ]] || { usage >&2; exit 2; }
output_dir=${M1_FORMAL_OUTPUT_DIR:-poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1}

case "$mode" in
  record)
    [[ -t 0 && -t 1 ]] || {
      printf 'Formal recording requires an attached local Pi terminal.\n' >&2
      exit 2
    }
    [[ -z "$(git status --porcelain)" ]] || {
      printf 'Pi worktree must be clean before Formal recording.\n' >&2
      exit 1
    }
    if fuser /dev/snd/* >/dev/null 2>&1; then
      printf 'An audio-device owner is already present; do not overlap recordings.\n' >&2
      exit 1
    fi
    bash poc_audio/tools/m1_fixture_record.sh --verify --stage pilot --output-dir "$output_dir"
    exec bash poc_audio/tools/m1_fixture_record.sh \
      --record-all --stage formal --confirm-authorization --output-dir "$output_dir"
    ;;
  verify)
    bash poc_audio/tools/m1_fixture_record.sh --verify --stage formal --output-dir "$output_dir"
    ;;
  list)
    bash poc_audio/tools/m1_fixture_record.sh --list --stage formal
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
