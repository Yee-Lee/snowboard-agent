#!/usr/bin/env bash
set -u
set -o pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run with sudo: sudo bash poc_llm/tools/run_gate1_arm64_measurement_batch.sh" >&2
  exit 2
fi

operator_uid="${SUDO_UID:?SUDO_UID is required}"
operator_gid="${SUDO_GID:?SUDO_GID is required}"
repo_root="$(git -c safe.directory="$PWD" rev-parse --show-toplevel)"
lock="poc_llm/harness/gate1-lock-arm64-wip-v1.json"
execution_sha="$(git -c safe.directory="$repo_root" -C "$repo_root" rev-parse HEAD)"
lock_sha="$(sha256sum "$repo_root/$lock" | awk '{print $1}')"
raw_root="/tmp/llm-poc-g1-arm64-measure-001"

for output_path in "$raw_root" "$raw_root-qwen15-result.json" "$raw_root-gemma-result.json"; do
  if [[ -e "$output_path" ]]; then
    echo "fresh-path requirement failed: $output_path already exists" >&2
    exit 2
  fi
done

cd "$repo_root" || exit 2
unshare --net --setuid "$operator_uid" --setgid "$operator_gid" -- bash -c '
  set -u
  set -o pipefail
  execution_sha="$1"
  lock_sha="$2"
  raw_root="$3"
  lock="$4"
  mkdir -p "$raw_root"
  python3 poc_llm/tools/run_gate1_arm64_measurement.py \
    --candidate-manifest poc_llm/fixtures/gate1/candidates-arm64/CAND-LRT-Q25-15B-Q8-R1.json \
    --lock "$lock" --lock-sha256 "$lock_sha" --execution-sha "$execution_sha" \
    --raw-dir "$raw_root/qwen15" | tee "$raw_root-qwen15-result.json"
  qwen_exit="${PIPESTATUS[0]}"
  python3 poc_llm/tools/run_gate1_arm64_measurement.py \
    --candidate-manifest poc_llm/fixtures/gate1/candidates-arm64/CAND-LRT-G4E2B-MOBILE-R1.json \
    --lock "$lock" --lock-sha256 "$lock_sha" --execution-sha "$execution_sha" \
    --raw-dir "$raw_root/gemma" | tee "$raw_root-gemma-result.json"
  gemma_exit="${PIPESTATUS[0]}"
  echo "qwen15_exit=$qwen_exit"
  echo "gemma_exit=$gemma_exit"
  if [[ "$qwen_exit" -eq 0 && "$gemma_exit" -eq 0 ]]; then
    echo "batch_exit=0"
    exit 0
  fi
  echo "batch_exit=1"
  exit 1
' arm64-measure "$execution_sha" "$lock_sha" "$raw_root" "$lock"
