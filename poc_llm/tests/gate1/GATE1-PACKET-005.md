# GATE1-PACKET-005 — Platform-keyed Config Projection

- **Packet ID**: `G1-X86-PI-COMPAT-005`
- **Status**: `R5 REPOSITORY REVISION / REAL EXECUTION BLOCKED`
- **Authority**: `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001`

R5 is append-only relative to accepted R4.  It preserves one logical candidate and pairing
revision, but replaces the singular candidate config with exact `configs.ubuntu-x86_64` and
`configs.pi-debian13-aarch64` entries.  Each entry is independently hashed and projected through
the unchanged M1 strict-config schema.  R4 is historical and is invalid as R5 evidence.

`gate1-lock-v5.json` authenticates the R5 candidate/acquisition schemas, catalog, projection
validator, two platform-owned entrypoints, R5 result/selection schemas, selector and Gate 2 guard.
The projection rejects absent/extra/legacy configs, duplicate config checksums, config swapping,
actual-file drift, cross-platform runtime/model paths, dependency or adapter drift and command
drift before an executable candidate process could be launched.

The versioned runners currently perform only authenticated pre-launch projection and return
`INCONCLUSIVE`: the Core ACK explicitly withholds real x86/Pi execution.  They do not produce
candidate, x86, Pi or Gate 2 evidence.  A later execution authorization must add the approved
operator/environment/raw-path inputs without weakening these identity checks.

## Deterministic regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-v5-pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet_v5
python3 poc_llm/harness/gate1_r5_validator.py \
  --lock poc_llm/harness/gate1-lock-v5.json \
  --catalog poc_llm/fixtures/gate1/gate1-r5-catalog.json --self-test
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-v4-pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet_v4
PYTHONPYCACHEPREFIX=/tmp/llm-poc-m1-pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_m1_contract
```

The fixtures are synthetic regression input only.  They are not candidate, hardware or Gate 2
evidence, and R5 itself does not authorize artifact transfer, install, x86 execution, Pi access,
network switching, finalist selection, baseline selection or product integration.
