#!/usr/bin/env bash
# Pi-local M1 native ALSA capability and lifecycle packet.
# It stores no captured audio and plays digital silence only.
set -euo pipefail

evidence_dir=${1:-"poc_audio/evidence/m1/$(date -u +%Y%m%dT%H%M%SZ)-native"}
capture_override=${M1_CAPTURE_DEVICE:-}
playback_override=${M1_PLAYBACK_DEVICE:-}
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)

mkdir -p "$evidence_dir"

result_file="$evidence_dir/result.txt"
environment_file="$evidence_dir/environment.txt"
matrix_file="$evidence_dir/matrix.tsv"
details_file="$evidence_dir/probe-details.txt"
lifecycle_file="$evidence_dir/lifecycle.txt"

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
  printf 'M1 native audio capability is INCONCLUSIVE: %s\n' "$1" >&2
  exit 2
}

for command_name in aplay arecord awk fuser git grep mktemp sed sha256sum timeout tr; do
  command -v "$command_name" >/dev/null 2>&1 || inconclusive "required command unavailable: $command_name"
done

[[ -z "$(git -C "$repo_root" status --porcelain)" ]] || inconclusive 'Pi Git worktree is dirty'
repo_sha=$(git -C "$repo_root" rev-parse HEAD)
[[ "$repo_sha" =~ ^[0-9a-f]{40}$ ]] || inconclusive 'full repository SHA is unavailable'

find_voicehat_pair() {
  local list_command=$1
  "$list_command" -l 2>/dev/null |
    sed -nE '/voicehat|googlevoi/I{s/^card ([0-9]+):.*device ([0-9]+):.*/\1,\2/p;q;}'
}

capture_pair=$(find_voicehat_pair arecord)
playback_pair=$(find_voicehat_pair aplay)
capture_device=${capture_override:-${capture_pair:+hw:$capture_pair}}
playback_device=${playback_override:-${playback_pair:+hw:$playback_pair}}

[[ "$capture_device" =~ ^hw:[A-Za-z0-9_-]+,[0-9]+$ ]] || inconclusive 'native capture device was not identified'
[[ "$playback_device" =~ ^hw:[A-Za-z0-9_-]+,[0-9]+$ ]] || inconclusive 'native playback device was not identified'

if fuser /dev/snd/* >/dev/null 2>&1; then
  inconclusive 'audio device is already owned before the packet'
fi

config_path=/boot/firmware/config.txt
config_sha=unavailable
config_audio_lines=unavailable
if [[ -r "$config_path" ]]; then
  config_sha=$(sha256sum "$config_path" | awk '{print $1}')
  config_audio_lines=$(sed -nE '/^[[:space:]]*(dtparam=i2s=on|dtoverlay=googlevoicehat-soundcard)[[:space:]]*$/p' "$config_path" | tr '\n' ';')
  [[ -n "$config_audio_lines" ]] || config_audio_lines=none
fi

{
  printf 'test_id=M1-NATIVE-AUDIO-001\n'
  printf 'tested_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'repo_sha=%s\n' "$repo_sha"
  printf 'model='; tr -d '\000' </proc/device-tree/model; printf '\n'
  printf 'architecture='; uname -m
  printf 'kernel='; uname -r
  printf 'os='; . /etc/os-release; printf '%s\n' "$PRETTY_NAME"
  printf 'capture_device=%s\n' "$capture_device"
  printf 'playback_device=%s\n' "$playback_device"
  printf 'audio_config_sha256=%s\n' "$config_sha"
  printf 'audio_config_lines=%s\n' "$config_audio_lines"
  printf 'temp_mC='; cat /sys/class/thermal/thermal_zone0/temp
  printf 'throttled='; (vcgencmd get_throttled 2>&1 || true)
  printf 'capture_devices_begin\n'; arecord -l 2>&1; printf 'capture_devices_end\n'
  printf 'playback_devices_begin\n'; aplay -l 2>&1; printf 'playback_devices_end\n'
} >"$environment_file"

printf 'direction\trequested_rate_hz\tactual_rate_hz\tchannels\tformat\texit_code\trate_mismatch\txrun_text\tresult\n' >"$matrix_file"
: >"$details_file"
: >"$lifecycle_file"

declare -A capture_pass=()
declare -A playback_pass=()
rates=(16000 44100 48000)
channels_list=(1 2)
formats=(S16_LE S24_LE S32_LE)

record_probe() {
  local direction=$1
  local rate=$2
  local channels=$3
  local format=$4
  local exit_code=$5
  local output=$6
  local actual_rate=$rate
  local rate_mismatch=none
  local xrun_text=none
  local result=FAIL

  if printf '%s\n' "$output" | grep -Fqi 'rate is not accurate'; then
    rate_mismatch=present
    actual_rate=$(printf '%s\n' "$output" | sed -nE 's/.*got = ([0-9]+)Hz.*/\1/p' | sed -n '1p')
    [[ -n "$actual_rate" ]] || actual_rate=unknown
  fi
  if printf '%s\n' "$output" | grep -Eqi '(^|[^a-z])(xrun|overrun|underrun)([^a-z]|$)'; then
    xrun_text=present
  fi
  if [[ "$exit_code" == 0 && "$rate_mismatch" == none && "$xrun_text" == none ]]; then
    result=PASS
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$direction" "$rate" "$actual_rate" "$channels" "$format" "$exit_code" \
    "$rate_mismatch" "$xrun_text" "$result" >>"$matrix_file"
  {
    printf '[%s rate=%s channels=%s format=%s exit=%s]\n' "$direction" "$rate" "$channels" "$format" "$exit_code"
    printf '%s\n' "$output"
  } >>"$details_file"
  [[ "$result" == PASS ]]
}

run_capture() {
  local rate=$1
  local channels=$2
  local format=$3
  local output
  local exit_code
  set +e
  output=$(timeout 5 arecord -D "$capture_device" -t raw -d 1 -r "$rate" -c "$channels" -f "$format" /dev/null 2>&1)
  exit_code=$?
  set -e
  record_probe capture "$rate" "$channels" "$format" "$exit_code" "$output"
}

run_playback() {
  local rate=$1
  local channels=$2
  local format=$3
  local output
  local exit_code
  set +e
  output=$(timeout 5 aplay -D "$playback_device" -t raw -d 1 -r "$rate" -c "$channels" -f "$format" /dev/zero 2>&1)
  exit_code=$?
  set -e
  record_probe playback "$rate" "$channels" "$format" "$exit_code" "$output"
}

for rate in "${rates[@]}"; do
  for channels in "${channels_list[@]}"; do
    for format in "${formats[@]}"; do
      key="$rate:$channels:$format"
      if run_capture "$rate" "$channels" "$format"; then
        capture_pass["$key"]=1
      fi
      if run_playback "$rate" "$channels" "$format"; then
        playback_pass["$key"]=1
      fi
    done
  done
done

target_key=16000:1:S16_LE
target_contract=FAIL
[[ -n "${capture_pass[$target_key]:-}" ]] && target_contract=PASS
printf 'native_16k_mono_s16=%s\n' "$target_contract" >>"$lifecycle_file"

set +e
period_output=$(timeout 5 arecord -D "$capture_device" -t raw -d 1 -r 16000 -c 1 -f S16_LE \
  --period-size=320 --buffer-size=1280 /dev/null 2>&1)
period_exit=$?
set -e
period_result=FAIL
if [[ "$period_exit" == 0 ]] &&
   ! printf '%s\n' "$period_output" | grep -Eqi '(^|[^a-z])(xrun|overrun|underrun)([^a-z]|$)'; then
  period_result=PASS
fi
printf 'native_16k_mono_s16_period_320=%s\n' "$period_result" >>"$lifecycle_file"
{
  printf '[capture-20ms-period exit=%s]\n' "$period_exit"
  printf '%s\n' "$period_output"
} >>"$details_file"

first_capture_key=
first_playback_key=
common_key=
preferences=(
  48000:2:S16_LE 48000:2:S24_LE 48000:2:S32_LE
  44100:2:S16_LE 44100:2:S24_LE 44100:2:S32_LE
  16000:1:S16_LE 16000:1:S24_LE 16000:1:S32_LE
)
for preference in "${preferences[@]}"; do
  [[ -n "$first_capture_key" || -z "${capture_pass[$preference]:-}" ]] || first_capture_key=$preference
  [[ -n "$first_playback_key" || -z "${playback_pass[$preference]:-}" ]] || first_playback_key=$preference
  if [[ -z "$common_key" && -n "${capture_pass[$preference]:-}" && -n "${playback_pass[$preference]:-}" ]]; then
    common_key=$preference
  fi
done

[[ -n "$first_capture_key" ]] || inconclusive 'no supported capture configuration was found'
[[ -n "$first_playback_key" ]] || inconclusive 'no supported playback configuration was found'

dump_hw_params() {
  local direction=$1
  local key=$2
  local rate channels format output exit_code
  IFS=: read -r rate channels format <<<"$key"
  set +e
  if [[ "$direction" == capture ]]; then
    output=$(timeout 5 arecord --dump-hw-params -D "$capture_device" -t raw -d 1 \
      -r "$rate" -c "$channels" -f "$format" /dev/null 2>&1)
  else
    output=$(timeout 5 aplay --dump-hw-params -D "$playback_device" -t raw -d 1 \
      -r "$rate" -c "$channels" -f "$format" /dev/zero 2>&1)
  fi
  exit_code=$?
  set -e
  {
    printf '[%s-hw-params key=%s exit=%s]\n' "$direction" "$key" "$exit_code"
    printf '%s\n' "$output"
  } >>"$details_file"
}

dump_hw_params capture "$first_capture_key"
dump_hw_params playback "$first_playback_key"

run_reopen() {
  local direction=$1
  local key=$2
  local rate channels format
  local passed=0
  IFS=: read -r rate channels format <<<"$key"
  for _ in 1 2 3; do
    if [[ "$direction" == capture ]]; then
      run_capture "$rate" "$channels" "$format" && passed=$((passed + 1))
    else
      run_playback "$rate" "$channels" "$format" && passed=$((passed + 1))
    fi
  done
  printf '%s_reopen_passes=%s/3\n' "$direction" "$passed" >>"$lifecycle_file"
  [[ "$passed" == 3 ]]
}

capture_reopen=FAIL
playback_reopen=FAIL
run_reopen capture "$first_capture_key" && capture_reopen=PASS
run_reopen playback "$first_playback_key" && playback_reopen=PASS

run_sequential_rates() {
  local direction=$1
  local first_key=$2
  local second_key=
  local first_rate candidate candidate_rate rate channels format
  local passed=0
  first_rate=${first_key%%:*}
  for candidate in "${preferences[@]}"; do
    candidate_rate=${candidate%%:*}
    [[ "$candidate_rate" != "$first_rate" ]] || continue
    if [[ "$direction" == capture && -n "${capture_pass[$candidate]:-}" ]]; then
      second_key=$candidate
      break
    fi
    if [[ "$direction" == playback && -n "${playback_pass[$candidate]:-}" ]]; then
      second_key=$candidate
      break
    fi
  done
  if [[ -z "$second_key" ]]; then
    printf '%s_sequential_different_rate=UNAVAILABLE\n' "$direction" >>"$lifecycle_file"
    return 0
  fi
  for candidate in "$first_key" "$second_key" "$first_key"; do
    IFS=: read -r rate channels format <<<"$candidate"
    if [[ "$direction" == capture ]]; then
      run_capture "$rate" "$channels" "$format" && passed=$((passed + 1))
    else
      run_playback "$rate" "$channels" "$format" && passed=$((passed + 1))
    fi
  done
  if [[ "$passed" == 3 ]]; then
    printf '%s_sequential_different_rate=PASS keys=%s,%s,%s\n' \
      "$direction" "$first_key" "$second_key" "$first_key" >>"$lifecycle_file"
  else
    printf '%s_sequential_different_rate=FAIL keys=%s,%s,%s\n' \
      "$direction" "$first_key" "$second_key" "$first_key" >>"$lifecycle_file"
  fi
}

run_sequential_rates capture "$first_capture_key"
run_sequential_rates playback "$first_playback_key"

concurrent_result=INCONCLUSIVE
capture_pid=
probe_tmp=$(mktemp -d)
cleanup_concurrent() {
  if [[ -n "$capture_pid" ]] && kill -0 "$capture_pid" 2>/dev/null; then
    kill -TERM "$capture_pid" 2>/dev/null || true
    wait "$capture_pid" 2>/dev/null || true
  fi
  rm -f "$probe_tmp/capture.txt" "$probe_tmp/playback.txt"
  rmdir "$probe_tmp" 2>/dev/null || true
}
trap cleanup_concurrent EXIT

if [[ -n "$common_key" ]]; then
  IFS=: read -r common_rate common_channels common_format <<<"$common_key"
  timeout 6 arecord -D "$capture_device" -t raw -d 2 -r "$common_rate" \
    -c "$common_channels" -f "$common_format" /dev/null >"$probe_tmp/capture.txt" 2>&1 &
  capture_pid=$!
  sleep 0.25
  set +e
  timeout 5 aplay -D "$playback_device" -t raw -d 1 -r "$common_rate" \
    -c "$common_channels" -f "$common_format" /dev/zero >"$probe_tmp/playback.txt" 2>&1
  concurrent_playback_exit=$?
  wait "$capture_pid"
  concurrent_capture_exit=$?
  set -e
  capture_pid=
  concurrent_result=FAIL
  if [[ "$concurrent_capture_exit" == 0 && "$concurrent_playback_exit" == 0 ]] &&
     ! grep -Eqi '(^|[^a-z])(xrun|overrun|underrun)([^a-z]|$)' "$probe_tmp/capture.txt" "$probe_tmp/playback.txt"; then
    concurrent_result=PASS
  fi
  {
    printf '[concurrent key=%s capture_exit=%s playback_exit=%s]\n' "$common_key" "$concurrent_capture_exit" "$concurrent_playback_exit"
    sed -n '1,120p' "$probe_tmp/capture.txt"
    sed -n '1,120p' "$probe_tmp/playback.txt"
  } >>"$details_file"
fi
printf 'shared_clock_concurrent=%s\n' "$concurrent_result" >>"$lifecycle_file"

cleanup_concurrent
trap - EXIT

cleanup_result=PASS
if fuser /dev/snd/* >/dev/null 2>&1; then
  cleanup_result=FAIL
fi
printf 'audio_device_owners_after=%s\n' "$cleanup_result" >>"$lifecycle_file"

final_result=FAIL
final_reason='one or more M1 target capability conditions failed'
if [[ "$target_contract" == PASS && "$capture_reopen" == PASS &&
      "$playback_reopen" == PASS && "$cleanup_result" == PASS ]]; then
  final_result=PASS
  final_reason='native target format, reopen lifecycle, and cleanup passed; capability boundaries are reported separately'
fi

write_result "$final_result" "$final_reason"
printf 'M1 native audio capability result: %s; evidence: %s\n' "$final_result" "$evidence_dir"
[[ "$final_result" == PASS ]]
