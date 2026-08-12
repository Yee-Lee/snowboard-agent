#!/usr/bin/env bash
# Pi-local SSD1351 build, lifecycle, negative-path and latency packet.
set -euo pipefail

config_path=${1:?usage: m3_ssd1351_capability.sh config.json [evidence-directory]}
evidence_dir=${2:-"poc_display/evidence/m3/$(date -u +%Y%m%dT%H%M%SZ)-ssd1351"}
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
native_dir="$repo_root/src/sbd/core/display/native/waveshare_ssd1351"
so_path="$native_dir/libdisplay.so"

mkdir -p "$(dirname "$evidence_dir")"
mkdir "$evidence_dir" || { printf '%s\n' 'evidence directory already exists' >&2; exit 2; }

result_file="$evidence_dir/result.txt"
environment_file="$evidence_dir/environment.txt"
build_file="$evidence_dir/build.log"
artifacts_file="$evidence_dir/artifacts.sha256"
lifecycle_file="$evidence_dir/lifecycle.txt"
visual_file="$evidence_dir/visual-checklist.txt"

write_result() {
  local result=$1
  local reason=$2
  {
    printf 'result=%s\n' "$result"
    printf 'reason=%s\n' "$reason"
  } >"$result_file"
}

inconclusive() {
  write_result 'INCONCLUSIVE' "$1"
  printf 'M3 SSD1351 capability is INCONCLUSIVE: %s\n' "$1" >&2
  exit 2
}

fail() {
  write_result 'FAIL' "$1"
  printf 'M3 SSD1351 capability failed: %s\n' "$1" >&2
  exit 1
}

on_exit() {
  local exit_code=$?
  if [[ ! -e "$result_file" ]]; then
    write_result 'FAIL' "unexpected packet exit code $exit_code"
  fi
}
trap on_exit EXIT

for command_name in awk cc fuser git grep ldd make python3 sed sha256sum timeout tr; do
  command -v "$command_name" >/dev/null 2>&1 || inconclusive "required command unavailable: $command_name"
done

[[ -r "$config_path" ]] || inconclusive 'local display config is unavailable'
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || inconclusive 'Pi Git worktree is dirty'
repo_sha=$(git -C "$repo_root" rev-parse HEAD)
[[ "$repo_sha" =~ ^[0-9a-f]{40}$ ]] || inconclusive 'full repository SHA is unavailable'

model=$(tr -d '\000' </proc/device-tree/model)
architecture=$(uname -m)
[[ "$model" == Raspberry\ Pi\ 5* ]] || inconclusive 'target is not Raspberry Pi 5'
[[ "$architecture" == aarch64 ]] || inconclusive 'target is not aarch64'

mapfile -t config_values < <(
  PYTHONPATH="$repo_root/src" python3 - "$config_path" <<'PY'
import json
import sys
from sbd.core.display.hal.profiles import load_display_config

path = sys.argv[1]
load_display_config(path)
data = json.load(open(path, encoding="utf-8"))
print(data["spi"]["device"])
print(data["gpio"]["chip"])
print(data["spi"]["requested_speed_hz"])
print(data["panel"]["revision"] or "")
PY
)
[[ "${#config_values[@]}" == 4 ]] || inconclusive 'strict display config validation failed'
spi_device=${config_values[0]}
gpio_chip=${config_values[1]}
requested_speed_hz=${config_values[2]}
config_panel_revision=${config_values[3]}
[[ "$spi_device" =~ ^/dev/spidev[0-9]+\.[0-9]+$ ]] || inconclusive 'configured SPI device is invalid'
[[ "$gpio_chip" =~ ^[0-9]+$ ]] || inconclusive 'configured gpiochip is unresolved'
gpio_device="/dev/gpiochip$gpio_chip"
[[ -c "$spi_device" ]] || inconclusive 'configured SPI device is absent'
[[ -c "$gpio_device" ]] || inconclusive 'configured gpiochip device is absent'

if fuser "$spi_device" "$gpio_device" >/dev/null 2>&1; then
  inconclusive 'SPI or GPIO device has an owner before the packet'
fi

config_sha=$(sha256sum "$config_path" | awk '{print $1}')
boot_config=/boot/firmware/config.txt
boot_config_sha=unavailable
spi_config_lines=unavailable
if [[ -r "$boot_config" ]]; then
  boot_config_sha=$(sha256sum "$boot_config" | awk '{print $1}')
  spi_config_lines=$(sed -nE '/^[[:space:]]*dtparam=spi=on[[:space:]]*$/p' "$boot_config" | tr '\n' ';')
  [[ -n "$spi_config_lines" ]] || spi_config_lines=none
fi

{
  printf 'test_id=M3-NATIVE-DISPLAY-001\n'
  printf 'tested_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'repo_sha=%s\n' "$repo_sha"
  printf 'model=%s\n' "$model"
  printf 'architecture=%s\n' "$architecture"
  printf 'kernel=%s\n' "$(uname -r)"
  printf 'os='; . /etc/os-release; printf '%s\n' "$PRETTY_NAME"
  printf 'python=%s\n' "$(python3 --version 2>&1)"
  printf 'compiler=%s\n' "$(cc --version | sed -n '1p')"
  printf 'lgpio_package=%s\n' "$(dpkg-query -W -f='${Version}' liblgpio-dev 2>/dev/null || printf 'unavailable')"
  printf 'display_config_sha256=%s\n' "$config_sha"
  printf 'boot_config_sha256=%s\n' "$boot_config_sha"
  printf 'spi_config_lines=%s\n' "$spi_config_lines"
  printf 'spi_device=%s\n' "$spi_device"
  printf 'gpio_device=%s\n' "$gpio_device"
  printf 'requested_speed_hz=%s\n' "$requested_speed_hz"
  printf 'temp_mC='; cat /sys/class/thermal/thermal_zone0/temp
  printf 'throttled='; (vcgencmd get_throttled 2>&1 || true)
} >"$environment_file"

{
  printf '[make clean]\n'
  timeout 60 make -C "$native_dir" clean
  printf '[make]\n'
  timeout 180 make -C "$native_dir"
} >"$build_file" 2>&1 || fail 'clean native build failed'

[[ -f "$so_path" ]] || fail 'native build did not produce libdisplay.so'

{
  printf '[ldd -r]\n'
  ldd -r "$so_path"
} >>"$build_file" 2>&1 || fail 'native library has unresolved runtime symbols'
sha256sum \
  "$so_path" \
  "$config_path" >"$artifacts_file"

runner_dir="$evidence_dir/runner"
set +e
PYTHONPATH="$repo_root/src" timeout 240 python3 \
  "$repo_root/poc_display/tests/run_ssd1351_diagnostics.py" \
  --config "$config_path" \
  --so "$so_path" \
  --output "$runner_dir" \
  --warmup 10 \
  --samples 100 \
  --observe-seconds 1 \
  >"$evidence_dir/diagnostics.log" 2>&1
runner_exit=$?
set -e
[[ "$runner_exit" == 0 ]] || fail "diagnostics runner failed with exit code $runner_exit"

if ! PYTHONPATH="$repo_root/src" python3 - "$runner_dir/latency.json" "$repo_sha" >"$lifecycle_file" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
expected_sha = sys.argv[2]
checks = {
    "source_sha_matches": data.get("source_sha") == expected_sha,
    "source_clean": data.get("source_dirty") is False,
    "wrong_length_rejected": data.get("wrong_length_rejected") is True,
    "missing_device_rejected": data.get("missing_device_rejected") is True,
    "reopen_3x": data.get("reopen_passes") == "3/3",
    "sample_count_100": data.get("sample_count", 0) >= 100,
    "p50_recorded": isinstance(data.get("p50_ms"), (int, float)),
    "p95_recorded": isinstance(data.get("p95_ms"), (int, float)),
    "max_recorded": isinstance(data.get("max_ms"), (int, float)),
}
for name, passed in checks.items():
    print(f"{name}={'PASS' if passed else 'FAIL'}")
if not all(checks.values()):
    raise SystemExit(1)
PY
then
  fail 'diagnostic lifecycle or latency gate failed'
fi

cleanup_result=PASS
if fuser "$spi_device" "$gpio_device" >/dev/null 2>&1; then
  cleanup_result=FAIL
fi
printf 'display_device_owners_after=%s\n' "$cleanup_result" >>"$lifecycle_file"
[[ "$cleanup_result" == PASS ]] || fail 'SPI or GPIO owner remains after diagnostics'
[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || fail 'Pi worktree became dirty during packet'

panel_revision=${M3_PANEL_REVISION:-}
color_result=${M3_COLOR_RESULT:-INCONCLUSIVE}
fixture_result=${M3_FIXTURE_RESULT:-INCONCLUSIVE}
orientation_result=${M3_ORIENTATION_RESULT:-INCONCLUSIVE}
flicker_result=${M3_FLICKER_RESULT:-INCONCLUSIVE}
{
  printf 'panel_revision=%s\n' "${panel_revision:-unavailable}"
  printf 'config_panel_revision=%s\n' "${config_panel_revision:-unavailable}"
  printf 'fixture_and_wiring=%s\n' "$fixture_result"
  printf 'color_order=%s\n' "$color_result"
  printf 'orientation=%s\n' "$orientation_result"
  printf 'flicker=%s\n' "$flicker_result"
} >"$visual_file"

if [[ -z "$panel_revision" || "$panel_revision" != "$config_panel_revision" ||
      "$fixture_result" != PASS || "$color_result" != PASS ||
      "$orientation_result" != PASS || "$flicker_result" != PASS ]]; then
  inconclusive 'automated gates passed; operator fixture/revision/visual attestation is incomplete'
fi

write_result 'PASS' 'clean build, strict config, lifecycle, negative paths, latency, cleanup, and operator visual gates passed'
trap - EXIT
printf 'M3 SSD1351 capability result: PASS; raw evidence: %s\n' "$evidence_dir"
