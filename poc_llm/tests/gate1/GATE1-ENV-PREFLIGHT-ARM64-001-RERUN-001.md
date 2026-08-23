# GATE1-ENV-PREFLIGHT-ARM64-001 — Controlled Rerun 001

- **Environment**: `ENV-UTM-ARM64-001`
- **Original attempt**: retained at `/tmp/llm-poc-g1-env-arm64-001-result.json`
- **Original result**: `INCONCLUSIVE`
- **Correction**: accept a distinct network namespace with an empty IPv4 route table; a QEMU
  sysfs interface may remain visible even though it has no route
- **Evidence for correction**: operator verified distinct execution/host network namespaces and no IPv4 route entries; namespace inode values remain outside Git
- **Rerun raw path**: `/tmp/llm-poc-g1-env-arm64-001-rerun-001`
- **Rerun install path**: `/tmp/llm-poc-g1-env-arm64-001-install-rerun-001`
- **Rerun result path**: `/tmp/llm-poc-g1-env-arm64-001-result-rerun-001.json`
- **Host network namespace input**: operator-provided at execution; value remains outside Git
- **Retry budget after this run**: zero

All artifact identities, exclusions, result semantics and ARM64-only namespace rules remain
unchanged from `GATE1-ENV-PREFLIGHT-ARM64-001`. The original result and raw path must not be
deleted, reused or overwritten.
