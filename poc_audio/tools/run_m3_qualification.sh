#!/usr/bin/env bash
# Validate the approved M3 packet or run local fake lifecycle checks.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest="$repo_root/poc_audio/manifests/m3_risk_qualification_packet.json"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 validate | authorize | fake-lifecycle | formal-mode | summarize [args]" >&2
  exit 2
fi
mode="$1"
shift
case "$mode" in
  validate)
    [[ $# -eq 0 ]] || { echo "validate takes no additional arguments" >&2; exit 2; }
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m3_qualification \
      validate --packet "$manifest" --repo-root "$repo_root"
    ;;
  authorize)
    [[ $# -eq 4 && "$1" == "--signoff" && "$3" == "--core-root" ]] || {
      echo "usage: $0 authorize --signoff FILE --core-root DIR" >&2
      exit 2
    }
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m3_qualification \
      authorize --packet "$manifest" --repo-root "$repo_root" \
      --signoff "$2" --core-root "$4"
    ;;
  fake-lifecycle)
    [[ $# -eq 2 && "$1" == "--output" ]] || {
      echo "usage: $0 fake-lifecycle --output FILE" >&2
      exit 2
    }
    source_sha="$(git -C "$repo_root" rev-parse HEAD)"
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m3_qualification \
      fake-lifecycle --packet "$manifest" --repo-root "$repo_root" \
      --source-sha "$source_sha" --output "$2"
    ;;
  summarize)
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m3_summary \
      --packet "$manifest" --repo-root "$repo_root" "$@"
    ;;
  tts|asr-direct|asr-hal|vad-hal|candidate-lifecycle)
    command -v unshare >/dev/null || {
      echo "formal candidate inference requires unshare" >&2
      exit 3
    }
    unshare --user --map-root-user --net -- \
      env PYTHONPATH="$repo_root/poc_audio/src" \
      python3 -m audio_poc.m3_formal_hal \
      "$mode" --packet "$manifest" --repo-root "$repo_root" "$@"
    ;;
  preflight|capture|direct-pcm|hal-lifecycle)
    PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m3_formal_hal \
      "$mode" --packet "$manifest" --repo-root "$repo_root" "$@"
    ;;
  *)
    echo "formal M3 mode '$mode' is unavailable before Core sign-off and the pinned HAL backend" >&2
    exit 3
    ;;
esac
