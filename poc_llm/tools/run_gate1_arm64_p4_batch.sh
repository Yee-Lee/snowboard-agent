#!/usr/bin/env bash
set -u
set -o pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run with sudo: sudo bash poc_llm/tools/run_gate1_arm64_p4_batch.sh" >&2
  exit 2
fi
operator_uid="${SUDO_UID:?SUDO_UID is required}"
operator_gid="${SUDO_GID:?SUDO_GID is required}"
repo_root="$(git -c safe.directory="$PWD" rev-parse --show-toplevel)"
lock="poc_llm/harness/gate1-lock-arm64-wip-v1.json"
execution_sha="$(git -c safe.directory="$repo_root" -C "$repo_root" rev-parse HEAD)"
lock_sha="$(sha256sum "$repo_root/$lock" | awk '{print $1}')"
raw_root="/tmp/llm-poc-g1-arm64-p4-001"
for path in "$raw_root" "$raw_root-qwen15-result.json" "$raw_root-gemma-result.json"; do
  [[ ! -e "$path" ]] || { echo "fresh-path requirement failed: $path already exists" >&2; exit 2; }
done
cd "$repo_root" || exit 2
unshare --net --setuid "$operator_uid" --setgid "$operator_gid" -- bash -c '
  set -u
  set -o pipefail
  sha="$1"; lock_sha="$2"; root="$3"; lock="$4"
  mkdir -p "$root"
  python3 poc_llm/tools/run_gate1_arm64_p4.py \
    --candidate-manifest poc_llm/fixtures/gate1/candidates-arm64/CAND-LRT-Q25-15B-Q8-R1.json \
    --lock "$lock" --lock-sha256 "$lock_sha" --execution-sha "$sha" --raw-dir "$root/qwen15" \
    | tee "$root-qwen15-result.json"
  qwen_exit="${PIPESTATUS[0]}"
  python3 poc_llm/tools/run_gate1_arm64_p4.py \
    --candidate-manifest poc_llm/fixtures/gate1/candidates-arm64/CAND-LRT-G4E2B-MOBILE-R1.json \
    --lock "$lock" --lock-sha256 "$lock_sha" --execution-sha "$sha" --raw-dir "$root/gemma" \
    | tee "$root-gemma-result.json"
  gemma_exit="${PIPESTATUS[0]}"
  echo "p4_qwen15_exit=$qwen_exit"
  echo "p4_gemma_exit=$gemma_exit"
  [[ "$qwen_exit" -eq 0 && "$gemma_exit" -eq 0 ]]
' arm64-p4 "$execution_sha" "$lock_sha" "$raw_root" "$lock"
batch_exit="$?"
echo "p4_batch_exit=$batch_exit"
exit "$batch_exit"
