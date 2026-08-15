#!/usr/bin/env bash
# Build the P4 Option A sources offline from a verified artifact directory.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
manifest_path="$repo_root/poc_audio/manifests/option_a_candidates.json"

usage() {
  printf '%s\n' \
    'usage: run_option_a_a10_clean_build.sh --artifact-dir DIR --output DIR [--python PATH]'
}

artifact_dir=''
output_dir=''
python_bin=python3
while (($#)); do
  case "$1" in
    --artifact-dir)
      artifact_dir=${2:?--artifact-dir requires a directory}
      shift 2
      ;;
    --output)
      output_dir=${2:?--output requires a directory}
      shift 2
      ;;
    --python)
      python_bin=${2:?--python requires a path}
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

[[ -d "$artifact_dir" ]] || { printf 'artifact directory is unavailable\n' >&2; exit 2; }
[[ -n "$output_dir" && ! -e "$output_dir" ]] || {
  printf 'output directory must be a new path\n' >&2
  exit 2
}
[[ -r "$manifest_path" ]] || { printf 'candidate manifest is unavailable\n' >&2; exit 2; }
command -v "$python_bin" >/dev/null 2>&1 || { printf 'Python is unavailable\n' >&2; exit 2; }
for command_name in sha256sum tar cmake gcc g++ ldd; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'required command is unavailable: %s\n' "$command_name" >&2
    exit 2
  }
done

mkdir -p "$output_dir"
trap 'status=$?; if ((status != 0)); then printf "result=FAIL\nexit_code=%s\n" "$status" >"$output_dir/result.txt"; fi' EXIT
exec > >(tee "$output_dir/command.log") 2>&1

require_version() {
  local label=$1 expected=$2 actual=$3
  printf '%s=%s\n' "$label" "$actual"
  [[ "$actual" == "$expected" ]] || {
    printf 'unexpected %s: expected %s\n' "$label" "$expected" >&2
    exit 1
  }
}

require_version python_version 3.13.5 "$("$python_bin" -c 'import platform; print(platform.python_version())')"
require_version cmake_version 3.31.6 "$(cmake --version | awk 'NR == 1 {print $3}')"
require_version gcc_version 14.2.0 "$(gcc -dumpfullversion -dumpversion)"
require_version gxx_version 14.2.0 "$(g++ -dumpfullversion -dumpversion)"

find_single() {
  local pattern=$1
  local matches=()
  shopt -s nullglob
  matches=("$artifact_dir"/$pattern)
  shopt -u nullglob
  ((${#matches[@]} == 1)) || {
    printf 'expected exactly one artifact matching %s, found %s\n' "$pattern" "${#matches[@]}" >&2
    exit 1
  }
  printf '%s\n' "${matches[0]}"
}

verify_artifact() {
  local filename=$1 expected_sha=$2 actual_sha
  actual_sha=$(sha256sum "$artifact_dir/$filename" | awk '{print $1}')
  printf '%s  %s\n' "$actual_sha" "$filename" >>"$output_dir/artifact-checksums.txt"
  [[ "$actual_sha" == "$expected_sha" ]] || {
    printf 'checksum mismatch: %s\n' "$filename" >&2
    exit 1
  }
}

manifest_values=$("$python_bin" - "$manifest_path" <<'PY'
import json
import sys

document = json.load(open(sys.argv[1], encoding="utf-8"))
candidates = {item["name"]: item for item in document["candidates"]}
hashes = document["dependency_artifact_sha256"]
for name in ("pyalsaaudio", "samplerate"):
    candidate = candidates[name]
    print(candidate["source_filename"], candidate["source_sha256"], sep="\t")
for filename, key in (
    ("packaging-26.3-py3-none-any.whl", "packaging-26.3-wheel"),
    ("setuptools-82.0.0-py3-none-any.whl", "setuptools-82.0.0-wheel"),
    ("setuptools_scm-10.2.1-py3-none-any.whl", "setuptools-scm-10.2.1-wheel"),
    ("vcs_versioning-2.2.4-py3-none-any.whl", "vcs-versioning-2.2.4-wheel"),
    ("wheel-0.48.0-py3-none-any.whl", "wheel-0.48.0-wheel"),
    ("pybind11-f5fbe867.tar.gz", "pybind11-f5fbe867-source"),
    ("libsamplerate-c96f5e3d.tar.gz", "libsamplerate-c96f5e3d-source"),
):
    print(filename, hashes[key], sep="\t")
PY
)
while IFS=$'\t' read -r filename expected_sha; do
  verify_artifact "$filename" "$expected_sha"
done <<<"$manifest_values"

numpy_wheel=$(find_single 'numpy-2.4.2-cp313-*.whl')
numpy_sha=$(sha256sum "$numpy_wheel" | awk '{print $1}')
expected_numpy_sha=$("$python_bin" - "$manifest_path" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["dependency_artifact_sha256"]["numpy-2.4.2-cp313-aarch64-wheel"])
PY
)
printf '%s  %s\n' "$numpy_sha" "$(basename "$numpy_wheel")" >>"$output_dir/artifact-checksums.txt"
[[ "$numpy_sha" == "$expected_numpy_sha" ]] || { printf 'checksum mismatch: numpy wheel\n' >&2; exit 1; }

source_root="$output_dir/source"
mkdir -p "$source_root"
for source_name in samplerate-0.2.4 pybind11-f5fbe867 libsamplerate-c96f5e3d; do
  mkdir -p "$source_root/$source_name"
done
tar -xzf "$artifact_dir/samplerate-0.2.4.tar.gz" -C "$source_root/samplerate-0.2.4" --strip-components=1
tar -xzf "$artifact_dir/pybind11-f5fbe867.tar.gz" -C "$source_root/pybind11-f5fbe867" --strip-components=1
tar -xzf "$artifact_dir/libsamplerate-c96f5e3d.tar.gz" -C "$source_root/libsamplerate-c96f5e3d" --strip-components=1

build_env="$output_dir/build-env"
"$python_bin" -m venv "$build_env"
"$build_env/bin/python" -m pip install --no-index \
  "$artifact_dir/wheel-0.48.0-py3-none-any.whl" \
  "$artifact_dir/packaging-26.3-py3-none-any.whl" \
  "$artifact_dir/setuptools-82.0.0-py3-none-any.whl" \
  "$artifact_dir/setuptools_scm-10.2.1-py3-none-any.whl" \
  "$artifact_dir/vcs_versioning-2.2.4-py3-none-any.whl"

wheel_dir="$output_dir/wheels"
mkdir -p "$wheel_dir"
PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 "$build_env/bin/python" -m pip wheel \
  --no-index --no-build-isolation --no-deps --wheel-dir "$wheel_dir" \
  "$artifact_dir/pyalsaaudio-0.11.0.tar.gz"
CMAKE_ARGS="-DFETCHCONTENT_SOURCE_DIR_PYBIND11=$source_root/pybind11-f5fbe867 -DFETCHCONTENT_SOURCE_DIR_LIBSAMPLERATE=$source_root/libsamplerate-c96f5e3d" \
  PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 "$build_env/bin/python" -m pip wheel \
  --no-index --no-build-isolation --no-deps --wheel-dir "$wheel_dir" \
  "$source_root/samplerate-0.2.4"

pyalsa_wheel=$(find "$wheel_dir" -maxdepth 1 -type f -name 'pyalsaaudio-0.11.0-*.whl' -print -quit)
samplerate_wheel=$(find "$wheel_dir" -maxdepth 1 -type f -name 'samplerate-0.2.4-*.whl' -print -quit)
[[ -n "$pyalsa_wheel" && -n "$samplerate_wheel" ]] || {
  printf 'expected wheels were not built\n' >&2
  exit 1
}
sha256sum "$pyalsa_wheel" "$samplerate_wheel" >"$output_dir/generated-wheel-checksums.txt"

rerun_env="$output_dir/rerun-env"
"$python_bin" -m venv "$rerun_env"
PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 "$rerun_env/bin/python" -m pip install \
  --no-index --no-deps "$numpy_wheel" "$pyalsa_wheel" "$samplerate_wheel"
"$rerun_env/bin/python" -m pip check
"$rerun_env/bin/python" - <<'PY' >"$output_dir/runtime-identity.txt"
import importlib.metadata
import samplerate

for distribution in ("numpy", "pyalsaaudio", "samplerate"):
    print(f"{distribution}={importlib.metadata.version(distribution)}")
print(f"samplerate_module_version={samplerate.__version__}")
print(f"libsamplerate_version={samplerate.__libsamplerate_version__}")
PY
grep -qx 'numpy=2.4.2' "$output_dir/runtime-identity.txt"
grep -qx 'pyalsaaudio=0.11.0' "$output_dir/runtime-identity.txt"
grep -qx 'samplerate=0.2.4' "$output_dir/runtime-identity.txt"
grep -qx 'samplerate_module_version=0.2.4' "$output_dir/runtime-identity.txt"

find "$rerun_env" -type f \( -name 'samplerate*.so' -o -name 'alsaaudio*.so' \) -print0 |
  while IFS= read -r -d '' native_file; do
    sha256sum "$native_file"
    ldd "$native_file"
  done >"$output_dir/native-library-identity.txt"

{
  printf 'result=PASS\n'
  printf 'source_build=PASS\n'
  printf 'identity_rerun=PASS\n'
  printf 'network_package_index=DISABLED\n'
} >"$output_dir/result.txt"
