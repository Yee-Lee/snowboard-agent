#!/usr/bin/env bash
# Read-only workstation/Pi readiness check modelled on the Audio POC pre-test.
set -euo pipefail

target=${1:?usage: environment_pre_test.sh ssh-alias [evidence-directory]}
evidence_dir=${2:-"poc_display/evidence/m3/$(date -u +%Y%m%dT%H%M%SZ)-pretest"}
ssh_config=${M3_SSH_CONFIG:-}
pi_poc_repo=${PI_POC_REPO:-}
pi_display_config=${PI_DISPLAY_CONFIG:-}

mkdir -p "$evidence_dir"

fail() {
  printf 'result=FAIL\nreason=%s\n' "$1" >"$evidence_dir/result.txt"
  printf 'Display environment pre-test failed: %s\n' "$1" >&2
  exit 1
}

[[ -n "$ssh_config" && -r "$ssh_config" ]] || fail 'operator-managed SSH config is unavailable'
[[ "$pi_poc_repo" =~ ^/[A-Za-z0-9._/-]+$ ]] || fail 'Pi POC worktree path is unavailable or invalid'
[[ "$pi_display_config" =~ ^/[A-Za-z0-9._/-]+\.json$ ]] || fail 'Pi display config path is unavailable or invalid'

for command_name in git ssh shasum sed tr; do
  command -v "$command_name" >/dev/null 2>&1 || fail "local command unavailable: $command_name"
done

local_repo_sha=$(git rev-parse HEAD)
[[ "$local_repo_sha" =~ ^[0-9a-f]{40}$ ]] || fail 'local full Git SHA is unavailable'
[[ -z "$(git status --porcelain)" ]] || fail 'local Git worktree is dirty'

ssh_opts=(
  -F "$ssh_config"
  -o BatchMode=yes
  -o ConnectTimeout=8
  -o StrictHostKeyChecking=yes
)

remote_ssh() {
  ssh "${ssh_opts[@]}" "$target" "$@"
}

# Do not retain connection errors; they can disclose operator endpoints.
remote_ssh true >/dev/null 2>&1 || fail 'non-interactive remote connection failed'
remote_ssh "git -C '$pi_poc_repo' rev-parse --is-inside-work-tree" >/dev/null 2>&1 || fail 'configured Pi worktree is unavailable'
remote_ssh "test -r '$pi_display_config'" >/dev/null 2>&1 || fail 'configured Pi display config is unavailable'

pi_repo_sha=$(remote_ssh "git -C '$pi_poc_repo' rev-parse HEAD")
pi_dirty_files=$(remote_ssh "git -C '$pi_poc_repo' status --porcelain | wc -l" | tr -d '[:space:]')
config_values=$(remote_ssh "python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d[\"spi\"][\"device\"]); print(d[\"gpio\"][\"chip\"])' '$pi_display_config'")
spi_device=$(printf '%s\n' "$config_values" | sed -n '1p')
gpio_chip=$(printf '%s\n' "$config_values" | sed -n '2p')
[[ "$spi_device" =~ ^/dev/spidev[0-9]+\.[0-9]+$ ]] || fail 'display config SPI device is invalid'
[[ "$gpio_chip" =~ ^[0-9]+$ ]] || fail 'display config gpiochip is unresolved'
gpio_device="/dev/gpiochip$gpio_chip"

{
  printf 'test_id=M3-DISPLAY-ENV-PRETEST-001\n'
  printf 'tested_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'local_repo_sha=%s\n' "$local_repo_sha"
  printf 'pi_repo_sha=%s\n' "$pi_repo_sha"
  printf 'pi_dirty_files=%s\n' "$pi_dirty_files"
  printf 'display_config_sha256=%s\n' "$(remote_ssh "sha256sum '$pi_display_config' | awk '{print \$1}'")"
  printf 'spi_device=%s\n' "$spi_device"
  printf 'gpio_device=%s\n' "$gpio_device"
  remote_ssh 'set -eu
    printf "model="; tr -d "\000" </proc/device-tree/model; printf "\n"
    printf "architecture="; uname -m
    printf "kernel="; uname -r
    printf "os="; . /etc/os-release; printf "%s\n" "$PRETTY_NAME"
    printf "root_disk_bytes="; df -B1 / | awk "NR == 2 {printf \"total=%s available=%s use=%s\\n\", \$2, \$4, \$5}"
    printf "temp_mC="; cat /sys/class/thermal/thermal_zone0/temp
    printf "throttled="; (vcgencmd get_throttled 2>&1 || true)
    for tool_name in bash git make gcc python3 sha256sum fuser timeout; do
      if command -v "$tool_name" >/dev/null 2>&1; then
        printf "remote_tool_%s=available\\n" "$tool_name"
      else
        printf "remote_tool_%s=missing\\n" "$tool_name"
      fi
    done
    config_path=/boot/firmware/config.txt
    if [ -r "$config_path" ]; then
      printf "boot_config_sha256="; sha256sum "$config_path" | awk "{print \$1}"
      printf "spi_config_lines="; sed -nE "/^[[:space:]]*dtparam=spi=on[[:space:]]*$/p" "$config_path" | tr "\n" ";"; printf "\n"
    else
      printf "boot_config_sha256=unavailable\nspi_config_lines=unavailable\n"
    fi'
  if remote_ssh "test -c '$spi_device'"; then printf 'spi_device_present=yes\n'; else printf 'spi_device_present=no\n'; fi
  if remote_ssh "test -c '$gpio_device'"; then printf 'gpio_device_present=yes\n'; else printf 'gpio_device_present=no\n'; fi
  if remote_ssh "fuser '$spi_device' '$gpio_device' >/dev/null 2>&1"; then
    printf 'display_device_owners=present\n'
  else
    printf 'display_device_owners=none\n'
  fi
} >"$evidence_dir/environment.txt" 2>&1

grep -q '^model=Raspberry Pi 5' "$evidence_dir/environment.txt" || fail 'target is not Raspberry Pi 5'
grep -qx 'architecture=aarch64' "$evidence_dir/environment.txt" || fail 'target is not aarch64'
grep -q '^remote_tool_.*=missing$' "$evidence_dir/environment.txt" && fail 'required remote tool unavailable'
[[ "$pi_repo_sha" == "$local_repo_sha" ]] || fail 'Pi worktree SHA differs from local HEAD'
[[ "$pi_dirty_files" == 0 ]] || fail 'Pi Git worktree is dirty'
grep -qx 'spi_device_present=yes' "$evidence_dir/environment.txt" || fail 'configured SPI device is absent'
grep -qx 'gpio_device_present=yes' "$evidence_dir/environment.txt" || fail 'configured gpiochip device is absent'
grep -qx 'display_device_owners=none' "$evidence_dir/environment.txt" || fail 'SPI or GPIO device already has an owner'

printf 'result=PASS\n' >"$evidence_dir/result.txt"
printf 'Display environment pre-test passed; local evidence: %s\n' "$evidence_dir"
