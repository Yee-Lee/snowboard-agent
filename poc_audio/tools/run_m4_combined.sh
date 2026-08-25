#!/usr/bin/env bash
# Validate the User-approved M4 packet or run local fake protocol checks.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
packet="$repo_root/poc_audio/manifests/m4_combined_packet.json"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 validate | fake --output FILE | lock-fixtures --fixture-dir DIR --fixture-lock FILE --audio-execution-sha SHA | formal <p9_1|combined|failure> [formal arguments]" >&2
  exit 2
fi

mode="$1"
shift
case "$mode" in
  validate)
    [[ $# -eq 0 ]] || { echo "validate takes no additional arguments" >&2; exit 2; }
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m4_combined \
      validate --packet "$packet" --repo-root "$repo_root"
    ;;
  fake)
    [[ $# -eq 2 && "$1" == "--output" ]] || {
      echo "usage: $0 fake --output FILE" >&2
      exit 2
    }
    source_sha="$(git -C "$repo_root" rev-parse HEAD)"
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m4_combined \
      fake --packet "$packet" --repo-root "$repo_root" \
      --source-sha "$source_sha" --output "$2"
    ;;
  lock-fixtures)
    [[ $# -eq 6 && "$1" == "--fixture-dir" && "$3" == "--fixture-lock" && "$5" == "--audio-execution-sha" ]] || {
      echo "usage: $0 lock-fixtures --fixture-dir DIR --fixture-lock FILE --audio-execution-sha SHA" >&2
      exit 2
    }
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m4_combined \
      lock-fixtures --packet "$packet" --repo-root "$repo_root" \
      --fixture-dir "$2" --fixture-lock "$4" --audio-execution-sha "$6"
    ;;
  formal)
    [[ $# -ge 1 ]] || {
      echo "usage: $0 formal <p9_1|combined|failure> [formal arguments]" >&2
      exit 2
    }
    command -v unshare >/dev/null || {
      echo "formal M4 candidate inference requires unshare" >&2
      exit 3
    }
    unshare --user --map-root-user --net -- \
      env PYTHONPATH="$repo_root/poc_audio/src" OPENBLAS_NUM_THREADS=1 \
      python3 -m audio_poc.m4_formal "$1" --packet "$packet" --repo-root "$repo_root" "${@:2}"
    ;;
  *)
    echo "unknown M4 mode: $mode" >&2
    exit 3
    ;;
esac
