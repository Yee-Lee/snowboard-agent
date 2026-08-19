# M1 Deterministic Fake Observation 001

- **Observation ID**: `M1-FAKE-001`
- **Date**: 2026-08-19
- **Baseline code SHA**: `eeb00e341056ccef77c10ae8ca4bcbbbfa683d39`
- **Packet**: `G1-UBUNTU-PRESCREEN-003`
- **Role**: Developer / POC Team self-test
- **Result**: `PASS` for deterministic fake/regression scope only

## Commands and observations

```text
PYTHONPYCACHEPREFIX=/tmp/llm-poc-m1-pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
Ran 6 tests in 58.420s — OK

python3 poc_llm/harness/gate1_validator.py \
  --catalog poc_llm/fixtures/gate1/catalog.json --self-test
result=PASS; violations=[]
catalog_sha256=e0b23661f225a846d8ad237140aac4196a2cd5ebc15980be33603abd8befe50f
```

The suite covered official protocol flow, deterministic max-two selection, runner-owned log leak
detection, missing cold P4 evidence, leader-first orphan reconciliation and rejection of forged
`UNAVAILABLE` PASS inputs. JSON syntax checks and `git diff --check` also passed.

This is not Ubuntu candidate evidence, Pi evidence or Internal Tester confirmation. No runtime or
model artifact was installed or downloaded, and no candidate/finalist/winner result is claimed.
