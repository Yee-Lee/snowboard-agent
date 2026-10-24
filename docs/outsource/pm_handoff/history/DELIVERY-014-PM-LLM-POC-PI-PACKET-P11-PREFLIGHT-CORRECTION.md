# DELIVERY-014-PM-LLM-POC-PI-PACKET-P11-PREFLIGHT-CORRECTION

- **Date**: 2026-08-23
- **From**: LLM POC Team (M4b)
- **To**: Core Designer
- **Status**: `SOURCE REVISION CORRECTION — SAME ACK REQUEST`
- **Supersedes**: the source identity in `DELIVERY-013-PM-LLM-POC-PI-EXECUTION-PACKETS-REVIEW`
- **Reviewed source branch/commit**: `llm` / `66ff4b363da78eaab27123d1b675218d8021680d`

## Correction

Before Core responds to the pending packet-review request, LLM POC identified that the controllers
authenticated the installed native library hash but did not execute the P11 ELF header/linkage check
stated in the packet. The corrected source now fails closed before candidate launch unless the
installed native library is hash-identical, `ELF64`, `AArch64`, and has no unresolved `ldd`
dependencies. It also requires and records `vcgencmd get_throttled=0x0` at target preflight.

Both executable locks were updated in the same commit:

- `poc_llm/harness/gate1-pi-compat-lock-v6.json`
- `poc_llm/harness/gate2a-pi-lock-v1.json`

## Requested Core handling

Please review `DELIVERY-013` against commit
`66ff4b363da78eaab27123d1b675218d8021680d` rather than
`5a5b4f375fc40d523db2e654ef02a4d8c793845f`. This does not add candidates, change packet scope,
alter P5, authorize a Pi run, or require a second ACK category. The requested reply remains exactly:

1. `G1-PI-COMPAT-006`: accept for physical-Pi execution / revise / reject.
2. `G2A-PI-LLM-001`: freeze pending Gate 1 Finalist ACK / revise / reject.
