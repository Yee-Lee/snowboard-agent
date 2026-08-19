# Core Designer → LLM POC Team: Gate 1 Packet Revision 004 ACK

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-GATE1-PACKET-R4-ACK-001`
- **In response to**: `DELIVERY-003-PM-LLM-POC-GATE1-PACKET-R4`
- **Reviewed POC branch / commit**: `llm` / `a99009fd5378d987411f37686814c84a1cb2a713`
- **From**: Core Team Designer
- **To**: LLM POC Team
- **Date**: 2026-08-19
- **Status**: `ACCEPTED — PACKET REVISION COMPLETE / REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `No`

## 1. Decision

Core Designer accepts the repository-only Gate 1 packet Revision 004 at exact commit
`a99009fd5378d987411f37686814c84a1cb2a713`. Local `HEAD` and `origin/llm` both resolve to that
commit. The returned implementation provides the approved x86 full pre-screen、immutable max-two
preselection、bounded Pi compatibility try-run、no-backfill selection and Gate 2 carry-over guard.

Core verification completed successfully:

- Revision 004 regression suite: `9/9 OK`.
- Retained Revision 003 regression suite: `6/6 OK`.
- Gate 1 validator self-test: `PASS`.
- Gate 2A and Gate 2B plan-only validation: `PLAN_VALID`.

Revision 004 therefore requires no further packet code、schema、selector or regression-test change.
The earlier packet-review disposition of `Revision required` is withdrawn.

## 2. Manual on-site controls

By User product-risk decision, the following checks are not required as automated packet acceptance
conditions and do not block this ACK:

1. automatic binding of the externally supplied candidate SHA;
2. automatic verification of Raspberry Pi 5 / 4GB hardware identity;
3. automatic verification of the network-disabled proof.

These items will be checked manually on site by the responsible operator before or during the real
Gate 1 run. The existing run report or result record must identify the operator、run time and manual
Pass / Fail disposition. No new generic handshake、proof framework、schema field or negative
regression is required for these three controls.

This waiver is limited to the three automation checks above. It does not change candidate ranking、
the two-candidate maximum、same-cycle no-backfill、Pi compatibility result semantics、cleanup、Gate 1
evidence separation or the prohibition on carrying Gate 1 credit into Gate 2A.

## 3. Authorization boundary and next state

- The replacement packet `G1-X86-PI-COMPAT-004` is accepted for future Gate 1 use.
- This ACK does not authorize model/runtime download、artifact acquisition、storage allocation、real
  x86 execution、Pi access、artifact transfer/install、network switching or Pi execution.
- Those actions may begin only after the applicable User/owner approvals for the runner、raw path、
  capacity、Pi access and on-site operation are recorded.
- No candidate or finalist is selected by this ACK. Gate 1 evidence must be returned after the
  separately authorized real execution for the later finalist decision.
- Gate 2A remains blocked until Core issues a Gate 1 finalist ACK and separately approves the Gate 2A
  packet and execution prerequisites. Gate 2B retains its Audio final-reference dependency.

No response or repository revision is required from the LLM POC Team for Revision 004 acceptance.
The next LLM handoff is the real Gate 1 execution evidence after separate authorization.
