#!/bin/sh
set -eu
case "${1:-}" in 1|2) windows=$1 ;; *) echo 'Usage: run-pi-voice.sh 1|2' >&2; exit 2 ;; esac
repo=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
target=${M4B_TARGET_DIR:-"$HOME/m4b-target-20260913-sLrXyC"}
output_dir=$(mktemp -d "$target/user-voice-${windows}-XXXXXX")
chmod 700 "$output_dir"
echo "OUTPUT_DIR=$output_dir"
echo "收音最多 $windows 輪，每輪 10 秒。看到 READY 再自由提問。"
echo '不自動填充，不判定 PM／PR／PH；輸入、回覆和錯誤會保存。'
cd "$repo"
export PYTHONPATH="$repo/src:$repo"
exec "$target/user-diagnostic-runtime/bin/python" scripts/m4b_measurement.py \
    --audio-config "$target/input/audio-config.yaml" \
    --runtime-python "$target/input/llm-runtime/bin/python" \
    --model "$target/input/gemma-4-E2B-it.litertlm" \
    --product-profile "$repo/requirements/m4b/product-profile.json" \
    --artifact-lock "$target/input/llm-runtime/llm-artifacts.json" \
    --private-output "$output_dir" --candidate-sha "$(git rev-parse HEAD)" \
    --user-authorized-diagnostic --diagnostic-windows "$windows"
