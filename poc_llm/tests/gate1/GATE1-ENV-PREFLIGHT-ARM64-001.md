# GATE1-ENV-PREFLIGHT-ARM64-001 — ARM64 UTM Test Request

- **Parent design**: `G1-DUAL-UTM-PREFLIGHT-001`
- **Environment ID**: `ENV-UTM-ARM64-001`
- **Execution namespace**: ARM64 only; no x86_64 artifact, command, raw evidence or result is accepted
- **Baseline SHA**: `98a854a91f514efa12c3904576c2b652629e0bbd`
- **Authorization**: User-authorized ARM64 preflight on 2026-08-22
- **Core disposition**: separate review remains required; this request does not close an external gate
- **Raw path**: `/tmp/llm-poc-g1-env-arm64-001` (operator-controlled, must be fresh)
- **Sanitized result**: `poc_llm/evidence/gate1/env-preflight-arm64-001.json`
- **Retry limit**: one controlled rerun after the original environment failure is retained

## Immutable ARM64 Inputs

| Input | Required identity | Current admission state |
| --- | --- | --- |
| LiteRT-LM API wheel | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl`; SHA-256 `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` | unavailable |
| Offline dependency bundle | exact path and SHA-256 fixed after independent inspection | unavailable |
| ARM64 adapter/binding bundle | exact path and SHA-256 fixed after independent inspection | unavailable |
| Import/adapter argv | canonical argv and SHA-256 fixed from the inspected bundles | unavailable |

The x86_64 wheel, dependency closure, adapter bundle, commands and evidence paths are prohibited in
this request. They belong to a separate branch and request. Model weights, generation and candidate
ranking are also prohibited.

## Admission Command

Run from a clean checkout of the baseline SHA before creating the raw directory:

```text
uname -m
python3 --version
getconf GNU_LIBC_VERSION
systemd-detect-virt
test ! -e /tmp/llm-poc-g1-env-arm64-001
sha256sum <approved-arm64-wheel>
sha256sum <approved-arm64-dependency-bundle>
sha256sum <approved-arm64-adapter-binding-bundle>
```

The three literal artifact paths and the exact import/adapter argv may be frozen only after the
controlled offline bundle exists and is independently inspected. No interactive repair, network
fallback or package substitution is permitted.

## Admission Result Semantics

- Continue to isolated offline install/import/lifecycle only when the environment, acceleration,
  all three artifacts and exact commands are authenticated.
- Missing environment identity, acceleration proof, artifact, checksum, command or evidence is
  `INCONCLUSIVE`; it is not a runtime `FAIL`.
- A valid wrong-architecture artifact, unresolved native dependency or repeatable lifecycle failure
  after complete admission is `FAIL`.
- `PASS` requires three clean lifecycle repetitions and complete cleanup evidence; admission alone
  can never produce `PASS`.
