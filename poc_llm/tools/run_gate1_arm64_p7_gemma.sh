#!/usr/bin/env bash
set -u
set -o pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run with sudo: sudo bash poc_llm/tools/run_gate1_arm64_p7_gemma.sh" >&2
  exit 2
fi

operator_uid="${SUDO_UID:?SUDO_UID is required}"
operator_gid="${SUDO_GID:?SUDO_GID is required}"
repo_root="$(git -c safe.directory="$PWD" rev-parse --show-toplevel)"
lock="poc_llm/harness/gate1-lock-arm64-wip-v1.json"
execution_sha="$(git -c safe.directory="$repo_root" -C "$repo_root" rev-parse HEAD)"
lock_sha="$(sha256sum "$repo_root/$lock" | awk '{print $1}')"
raw_dir="/tmp/llm-poc-g1-arm64-p7-gemma-001"
result_path="$raw_dir-result.json"

for output_path in "$raw_dir" "$result_path"; do
  if [[ -e "$output_path" ]]; then
    echo "fresh-path requirement failed: $output_path already exists" >&2
    exit 2
  fi
done

cd "$repo_root" || exit 2
unshare --net --setuid "$operator_uid" --setgid "$operator_gid" -- \
  python3 poc_llm/tools/run_gate1_arm64_p7_recovery.py \
  --candidate-manifest poc_llm/fixtures/gate1/candidates-arm64/CAND-LRT-G4E2B-MOBILE-R1.json \
  --lock "$lock" \
  --lock-sha256 "$lock_sha" \
  --execution-sha "$execution_sha" \
  --raw-dir "$raw_dir" \
  | tee "$result_path"

runner_exit="${PIPESTATUS[0]}"
echo "p7_gemma_exit=$runner_exit"
exit "$runner_exit"
