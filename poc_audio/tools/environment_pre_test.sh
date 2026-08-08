#!/usr/bin/env bash
# Read-only readiness check for a developer workstation and the target Pi.
# Connection configuration is operator-managed and must remain outside Git.
set -euo pipefail

target=${1:?usage: environment_pre_test.sh ssh-alias [evidence-directory]}
evidence_dir=${2:-"poc_audio/evidence/m0/$(date -u +%Y%m%dT%H%M%SZ)-pretest"}
ssh_config=${M0_SSH_CONFIG:-}

fail() {
  printf 'result=FAIL\nreason=%s\n' "$1" >"$evidence_dir/result.txt"
  printf 'Environment pre-test failed: %s\n' "$1" >&2
  exit 1
}

mkdir -p "$evidence_dir"
[[ -n "$ssh_config" && -r "$ssh_config" ]] || fail 'operator-managed SSH config is unavailable'

for command_name in ssh scp shasum mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || fail "local command unavailable: $command_name"
done

ssh_opts=(
  -F "$ssh_config"
  -o BatchMode=yes
  -o ConnectTimeout=8
  -o StrictHostKeyChecking=yes
)
remote_ssh() {
  ssh "${ssh_opts[@]}" "$target" "$@"
}

# Keep connection errors out of evidence: they can contain operator-specific
# endpoints. The generic result records only that the precondition failed.
remote_ssh true >/dev/null 2>&1 || fail 'non-interactive remote connection failed'

{
  printf 'test_id=M0-ENV-PRETEST-001\n'
  printf 'tested_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'repo_sha=%s\n' "$(git rev-parse HEAD)"
  if [[ -n "$(git status --porcelain)" ]]; then
    printf 'repo_dirty=true\n'
  else
    printf 'repo_dirty=false\n'
  fi
  printf 'local_dependencies=PASS\n'
  remote_ssh 'set -eu
    printf "model="; tr -d "\000" </proc/device-tree/model; printf "\n"
    printf "architecture="; uname -m
    printf "kernel="; uname -r
    printf "os="; . /etc/os-release; printf "%s\n" "$PRETTY_NAME"
    printf "root_disk_bytes="; df -B1 / | awk "NR == 2 {printf \"total=%s available=%s use=%s\\n\", \$2, \$4, \$5}"
    printf "temp_mC="; cat /sys/class/thermal/thermal_zone0/temp
    printf "throttled="; (vcgencmd get_throttled 2>&1 || true)
    for tool_name in bash timeout setsid sha256sum arecord aplay fuser; do
      if command -v "$tool_name" >/dev/null 2>&1; then
        printf "remote_tool_%s=available\\n" "$tool_name"
      else
        printf "remote_tool_%s=missing\\n" "$tool_name"
      fi
    done
    printf "capture_device_count="; arecord -l 2>/dev/null | awk "/^card [0-9]+:/ {count++} END {print count + 0}"
    printf "playback_device_count="; aplay -l 2>/dev/null | awk "/^card [0-9]+:/ {count++} END {print count + 0}"
    if fuser /dev/snd/* >/dev/null 2>&1; then
      printf "audio_device_owners=present\\n"
    else
      printf "audio_device_owners=none\\n"
    fi'
} >"$evidence_dir/environment.txt" 2>&1

grep -q '^model=Raspberry Pi 5' "$evidence_dir/environment.txt" || fail 'target is not Raspberry Pi 5'
grep -qx 'architecture=aarch64' "$evidence_dir/environment.txt" || fail 'target is not aarch64'
grep -q '^remote_tool_.*=missing$' "$evidence_dir/environment.txt" && fail 'required remote tool unavailable'
grep -q '^capture_device_count=0$' "$evidence_dir/environment.txt" && fail 'no capture device detected'
grep -q '^playback_device_count=0$' "$evidence_dir/environment.txt" && fail 'no playback device detected'
grep -qx 'audio_device_owners=none' "$evidence_dir/environment.txt" || fail 'audio device already in use'

printf 'result=PASS\n' >"$evidence_dir/result.txt"
printf 'Environment pre-test passed; local evidence: %s\n' "$evidence_dir"
