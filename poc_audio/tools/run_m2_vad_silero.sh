#!/usr/bin/env bash
# Run the authorized conditional Silero M2 scorecard; never captures or plays audio.
set -euo pipefail

if [[ $# -ne 14 ]]; then
  echo "usage: $0 --runtime-python FILE --runtime-wheel-dir DIR --source-artifact FILE --model FILE --fixture-dir DIR --label-index FILE --output FILE" >&2
  exit 2
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || {
  echo "Silero scorecard requires a clean Git worktree" >&2
  exit 1
}
runtime_python=""; runtime_wheel_dir=""; source_artifact=""; model=""
fixture_dir=""; label_index=""; output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime-python) runtime_python="$2" ;;
    --runtime-wheel-dir) runtime_wheel_dir="$2" ;;
    --source-artifact) source_artifact="$2" ;;
    --model) model="$2" ;;
    --fixture-dir) fixture_dir="$2" ;;
    --label-index) label_index="$2" ;;
    --output) output="$2" ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift 2
done

PIP_NO_INDEX=1 PYTHONPATH="$repo_root/poc_audio/src" "$runtime_python" \
  -m audio_poc.m2_vad_silero \
  --source-artifact "$source_artifact" --model "$model" \
  --runtime-wheel-dir "$runtime_wheel_dir" --fixture-dir "$fixture_dir" \
  --label-index "$label_index" \
  --recording-plan "$repo_root/poc_audio/fixtures/authorized/recording_plan_v1.json" \
  --source-sha "$source_sha" --output "$output"
