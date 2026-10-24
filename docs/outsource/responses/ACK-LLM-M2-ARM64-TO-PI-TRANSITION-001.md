# ACK-LLM-M2-ARM64-TO-PI-TRANSITION-001

**Date**: 2026-08-23
**From**: Core Designer
**To**: LLM POC Team (M4b)
**In response to**: `DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION`
**Status**: `ACCEPTED WITH CONDITIONS — PI TRANSITION AUTHORIZED`

---

## 1. Dispositions on Requested Decisions

Core Designer has reviewed the engineering evidence and transition request submitted in `DELIVERY-011`
and issues the following formal decisions:

### Item 1: ARM64 UTM Pre-screen Acceptance
**ACCEPTED.** The Ubuntu 24.04 ARM64 UTM evidence is accepted as valid workstation pre-screen and
comparative engineering input. In accordance with the contract, no UTM run earns Gate 2 credit or milestone
completion.

### Item 2: Waiver of Independent x86_64 Track
**ACCEPTED.** The requirement to complete the independent x86_64 WIP track and resolve the two-branch
merge boundary is waived. Native ARM64 evidence aligns directly with the Raspberry Pi 5 aarch64 target architecture.

### Item 3: Candidate Freeze (Maximum Two Finalists)
**ACCEPTED.**
- Authorized candidates:
  1. `CAND-LRT-G4E2B-MOBILE-R1` (`gemma-4-E2B-it.litertlm`)
  2. `CAND-LRT-Q25-15B-Q8-R1` (`Qwen2.5-1.5B-Instruct...litertlm`)
- Rejected: `CAND-LRT-Q25-05B-Q8-R1` is confirmed ineligible due to the unsupported MediaPipe `.task` container.
- No third candidate backfill is permitted.

### Item 4: P5 Contract Disposition
**ACCEPTED WITH CONDITION.** The 1000 ms workaround is accepted as proof of timeout handling mechanisms.
Contract P5 remains `INCONCLUSIVE` on workstation. Before freezing the Gate 2A packet, LLM POC must
provide a Pi-specific extreme-generation fixture or a formalized timeout test case to validate the 15-second
contract boundary on the physical Pi.

### Item 5: Transition of Acceptance to Independent Pi Packets
**ACCEPTED.** Mandatory acceptance items (P1–P8, P10A, P11, P12) will be executed on the physical Raspberry Pi 5
under dedicated Gate 2A packets rather than expanding the workstation UTM harness.

### Item 6: Milestone and Gate Controls
**CONFIRMED.** Milestone M2 and External Gate 1 remain `IN_PROGRESS` / `BLOCKED` until the physical Pi
compatibility packet is executed and verified. Gate 2A begins only after Core issues the formal Gate 1
Finalist ACK.

---

## 2. P9 Surrogate Acknowledgment

Core acknowledges receipt of `RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001`. The provided conservative resource
envelope (2304 MiB RSS / 4 cores / 6s startup / 6s inference) has been incorporated into
`DELIVERY-P9-SURROGATE-SPEC-001` and delivered to Audio POC.

---

## 3. Next Steps for LLM POC

1. Prepare the Pi compatibility packet targeting the two frozen `.litertlm` candidates.
2. Ensure deployment on clean Raspberry Pi 5 (4GB, Debian 13 aarch64, `swap=0`).
3. Submit the Gate 1 Pi Compatibility Packet for Core Designer review prior to scored execution.
