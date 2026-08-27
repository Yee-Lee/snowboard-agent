# LLM POC Gate 1 R5 Exact-SHA Review Request

- **Delivery ID**: `DELIVERY-008-PM-LLM-POC-M2-GATE1-R5-REVIEW`
- **From / via**: LLM POC Team / User-authorized Agent courier via PM
- **To**: Core Team Designer
- **In response to**: `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001`
- **Finding**: `M2-G1-PLATFORM-CONFIG-001`
- **Packet**: `G1-X86-PI-COMPAT-005`
- **Review target**: `llm` / `190a827b4c82279e4300af6075e2eeb52b91cd54`
- **Status**: `CORE EXACT-SHA REVIEW REQUESTED / REAL EXECUTION BLOCKED`
- **Architecture change**: `No`
- **Date**: 2026-08-22

## Decision requested

Please review and accept the immutable R5 repository target above. R5 preserves one logical
candidate/pairing identity while authenticating separate `ubuntu-x86_64` and
`pi-debian13-aarch64` strict configs, acquisition entries and runner projections. Acceptance of
this SHA closes only the repository packet revision; it does not authorize real execution or start
M2.

## Changed paths in the R5 target

- `docs/DOCUMENT_INDEX.md`
- `docs/milestone/README.md`
- `docs/pm_handoff/history/DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001.md`
- `docs/response/ACK-LLM-M2-GATE1-PLATFORM-CONFIG-R5-INTAKE-001.md`
- `poc_llm/evidence/gate1/gate1-r5-run-result.schema.json`
- `poc_llm/evidence/gate1/gate1-selection-v5.schema.json`
- `poc_llm/fixtures/gate1/acquisition-v5.schema.json`
- `poc_llm/fixtures/gate1/candidate-v5.schema.json`
- `poc_llm/fixtures/gate1/gate1-r5-catalog.json`
- `poc_llm/harness/gate1-lock-v5.json`
- `poc_llm/harness/gate1_r5_projection.py`
- `poc_llm/harness/gate1_r5_validator.py`
- `poc_llm/tests/gate1/GATE1-PACKET-005.md`
- `poc_llm/tests/gate1/test_gate1_packet_v5.py`
- `poc_llm/tools/run_gate1_pi_compat_v5.py`
- `poc_llm/tools/run_gate1_r5.py`
- `poc_llm/tools/run_gate1_x86_prescreen_v5.py`
- `poc_llm/tools/select_gate1_finalists_v5.py`

## Recorded deterministic verification

- R5 synthetic suite: 7/7 passed.
- R5 validator self-test: passed.
- Retained R4 deterministic suite: 9/9 passed.
- M1 contract suite: 20/20 passed.
- Protected M1 path diff from frozen candidate
  `830d0b4ed2d41406c789bb110ed84b7553f330a4`: empty.

The R4 cases were also invoked individually after the combined command exceeded the prior
workstation's single-command return limit. All recorded exit codes were 0. These are synthetic
repository regressions only, not candidate or hardware evidence.

## Preserved boundaries and remaining blockers

- No real Ubuntu x86 or Pi run, artifact transfer/install, network switch, finalist selection,
  Gate 2 evidence or product integration occurred.
- Candidate manifests remain blocked until Core accepts the exact R5 SHA.
- Real Gate 1 additionally requires an approved Ubuntu 24.04 x86 runner and capacity/raw paths,
  the product Pi operator/access/path, offline transfer/install procedure and explicit execution
  authorization.
- The current local checkout is a new macOS workstation and has no downloaded model bundle. It is
  not the authorized Ubuntu runner and contributes no Gate 1 execution evidence.
