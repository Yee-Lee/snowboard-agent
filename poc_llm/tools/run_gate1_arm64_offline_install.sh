#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 || -z "${SUDO_UID:-}" || -z "${SUDO_GID:-}" ]]; then
  echo "run through sudo from the authorized operator account" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
staging_root="/tmp/llm-poc-g1-arm64-001"
install_root="${staging_root}/install"
log_path="${staging_root}/offline-install-r2.txt"

if [[ -e "${install_root}" ]]; then
  echo "install target is dirty" >&2
  exit 2
fi

cd "${repo_root}"
set +e
unshare \
  --net \
  --setuid "${SUDO_UID}" \
  --setgid "${SUDO_GID}" \
  -- \
  bash -c '
    set -eu
    echo "interfaces:"
    ls -1 /sys/class/net
    echo "routes-v4:"
    cat /proc/net/route
    echo "routes-v6:"
    cat /proc/net/ipv6_route
    echo "namespace:"
    readlink /proc/self/ns/net

    python3 poc_llm/tools/install_gate1_arm64_wheel.py \
      --wheel /tmp/llm-poc-g1-arm64-001/bundle/litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl \
      --wheel-sha256 5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00 \
      --target /tmp/llm-poc-g1-arm64-001/install

    PYTHONPATH=/tmp/llm-poc-g1-arm64-001/install \
      PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-arm64-001/pycache \
      python3 -c "import importlib.metadata, litert_lm; from litert_lm._ffi import _get_lib; _get_lib(); print(importlib.metadata.version(\"litert-lm-api\")); print(\"NATIVE_IMPORT_OK\")"

    sha256sum /tmp/llm-poc-g1-arm64-001/install/litert_lm/liblitert-lm.so
    file /tmp/llm-poc-g1-arm64-001/install/litert_lm/liblitert-lm.so
    ldd /tmp/llm-poc-g1-arm64-001/install/litert_lm/liblitert-lm.so
  ' 2>&1 | tee "${log_path}"
status="${PIPESTATUS[0]}"
set -e

echo "offline_install_exit=${status}"
exit "${status}"
