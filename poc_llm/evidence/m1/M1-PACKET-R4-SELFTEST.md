# M1 Gate 1 Packet Revision 004 Self-test

- **Observation ID**: `M1-PACKET-R4-SELFTEST`
- **Date**: 2026-08-19
- **Packet**: `G1-X86-PI-COMPAT-004`
- **Role**: Developer / POC Team deterministic self-test
- **Result**: `PASS` for packet/regression scope only

## Results

```text
python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet_v4
Ran 9 tests in 36.732s — OK

python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
Ran 6 tests in 68.033s — OK

python3 poc_llm/harness/gate1_validator.py \
  --catalog poc_llm/fixtures/gate1/catalog.json --self-test
result=PASS; violations=[]

gate1-lock-v4 integrity: 13 artifacts checked — PASS
Draft 2020-12 schema check: 6 schemas — PASS
Gate 2A plan: PLAN_VALID; execution_performed=false
Gate 2B plan: PLAN_VALID; execution_performed=false
git diff --check: PASS
```

Revision-004 coverage includes immutable x86 max-two preselection、Pi PASS filtering、Pi
FAIL/INCONCLUSIVE、no third-candidate backfill、missing/forged identity、unapproved platform、
incomplete P4 arrays、dirty/reused raw paths、Pi cleanup/orphan failure and Gate 1 evidence
carry-over rejection at Gate 2A.

No model/runtime download、artifact acquisition/transfer/install、real x86 run、Pi compatibility
run、network switching、privilege/configuration change or Gate 2 execution occurred.
