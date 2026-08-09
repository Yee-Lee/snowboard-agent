#!/usr/bin/env bash
# M0-only remote-control and evidence-chain probe. This is intentionally not a
# product runtime component and must not run during performance measurements.
set -euo pipefail

target=${1:?usage: m0_remote_readiness.sh ssh-alias [evidence-directory]}
evidence_dir=${2:-"poc_audio/evidence/m0/$(date -u +%Y%m%dT%H%M%SZ)"}
ssh_config=${M0_SSH_CONFIG:-}
[[ -n "$ssh_config" && -r "$ssh_config" ]] || { printf '%s\n' 'Set M0_SSH_CONFIG to an operator-managed SSH config outside this repository.' >&2; exit 2; }
mkdir -p "$evidence_dir"

ssh_opts=(
  -F "$ssh_config"
  -o BatchMode=yes
  -o ConnectTimeout=8
  -o StrictHostKeyChecking=yes
)

remote_ssh() {
  ssh "${ssh_opts[@]}" "$target" "$@"
}

probe_pid=""
cleanup_probe() {
  if [[ -n "$probe_pid" ]]; then
    remote_ssh "if kill -0 '$probe_pid' 2>/dev/null; then kill -TERM '$probe_pid'; fi" || true
  fi
}
trap cleanup_probe EXIT

{
  printf 'test_id=M0-REMOTE-001\n'
  printf 'started_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  remote_ssh 'set -eu
    printf "model="; tr -d "\000" </proc/device-tree/model; printf "\n"
    printf "arch="; uname -m
    printf "kernel="; uname -r
    printf "os="; . /etc/os-release; printf "%s\n" "$PRETTY_NAME"
    printf "time="; date --iso-8601=seconds
    printf "load="; cat /proc/loadavg
    printf "memory_bytes="; free -b | awk "NR == 2 {printf \"total=%s available=%s\\n\", \$2, \$7}"
    printf "root_disk_bytes="; df -B1 / | awk "NR == 2 {printf \"total=%s available=%s use=%s\\n\", \$2, \$4, \$5}"
    printf "temp_mC="; cat /sys/class/thermal/thermal_zone0/temp
    printf "throttled="; (vcgencmd get_throttled 2>&1 || true)
    printf "audio_cards:\n"; cat /proc/asound/cards 2>&1 || true
    printf "capture_devices:\n"; arecord -l 2>&1 || true
    printf "playback_devices:\n"; aplay -l 2>&1 || true
    printf "audio_device_owners:\n"; fuser -v /dev/snd/* 2>&1 || true'
} >"$evidence_dir/environment.txt" 2>&1

set +e
remote_ssh 'exit 37'
exit_code=$?
set -e
printf 'remote_exit_code=%s\n' "$exit_code" >"$evidence_dir/command-control.txt"
[[ "$exit_code" == 37 ]]

set +e
remote_ssh 'timeout 2 sleep 20'
timeout_exit=$?
set -e
printf 'remote_timeout_exit_code=%s\n' "$timeout_exit" >>"$evidence_dir/command-control.txt"
[[ "$timeout_exit" == 124 ]]

probe_pid=$(remote_ssh 'setsid sleep 120 </dev/null >/dev/null 2>&1 & printf "%s\n" "$!"')
[[ "$probe_pid" =~ ^[0-9]+$ ]]
printf 'started_probe_pid=%s\n' "$probe_pid" >>"$evidence_dir/command-control.txt"
remote_ssh "test \"\$(ps -p '$probe_pid' -o comm= | tr -d ' ')\" = sleep"
remote_ssh "kill -TERM '$probe_pid'"
for _ in {1..10}; do
  if ! remote_ssh "kill -0 '$probe_pid' 2>/dev/null"; then
    break
  fi
  sleep 1
done
if remote_ssh "kill -0 '$probe_pid' 2>/dev/null"; then
  printf 'cancel_cleanup=FAIL\n' >>"$evidence_dir/command-control.txt"
  exit 1
fi
printf 'cancel_cleanup=PASS\n' >>"$evidence_dir/command-control.txt"
probe_pid=""

local_tmp=$(mktemp -d)
remote_tmp="/tmp/m0-transfer-$(date +%s)-$$.txt"
cleanup_transfer() {
  if [[ -n "$remote_tmp" ]]; then
    remote_ssh "rm -f '$remote_tmp'" || true
  fi
  rm -rf "$local_tmp"
}
trap 'cleanup_transfer; cleanup_probe' EXIT
printf 'm0-evidence-transfer\nsource=local\n' >"$local_tmp/source.txt"
local_sha=$(shasum -a 256 "$local_tmp/source.txt" | awk '{print $1}')
scp "${ssh_opts[@]}" "$local_tmp/source.txt" "$target:$remote_tmp"
remote_sha=$(remote_ssh "sha256sum '$remote_tmp' | awk '{print \$1}'")
scp "${ssh_opts[@]}" "$target:$remote_tmp" "$local_tmp/roundtrip.txt"
roundtrip_sha=$(shasum -a 256 "$local_tmp/roundtrip.txt" | awk '{print $1}')
{
  printf 'local_sha256=%s\n' "$local_sha"
  printf 'remote_sha256=%s\n' "$remote_sha"
  printf 'roundtrip_sha256=%s\n' "$roundtrip_sha"
} >"$evidence_dir/transfer.txt"
[[ "$local_sha" == "$remote_sha" && "$local_sha" == "$roundtrip_sha" ]]

remote_ssh "rm -f '$remote_tmp'; test ! -e '$remote_tmp'"
remote_tmp=""
printf 'transfer_temporary_cleanup=PASS\n' >>"$evidence_dir/transfer.txt"
if remote_ssh 'fuser /dev/snd/* >/dev/null 2>&1'; then
  printf 'audio_device_owners_after=FAIL\n' >>"$evidence_dir/command-control.txt"
  exit 1
fi
printf 'audio_device_owners_after=PASS\n' >>"$evidence_dir/command-control.txt"

printf 'result=PASS\n' >"$evidence_dir/result.txt"
printf 'M0 readiness probe passed; evidence: %s\n' "$evidence_dir"
