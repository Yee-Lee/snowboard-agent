# Gate 1 M2 Dual-UTM Preflight Plan ACK

- **Record ID**: `ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001`
- **In response to**: `DELIVERY-009-PM-LLM-POC-M2-DUAL-UTM-PREFLIGHT`
- **From**: Core Team Designer
- **To**: LLM POC Team via PM
- **Status**: `DESIGNER APPROVED — PREFLIGHT PACKET PREPARATION AUTHORIZED / REAL EXECUTION BLOCKED`
- **Date**: 2026-08-22

## 1. Decision on Prior Delivery

The exact-SHA acceptance for the R5 repository target requested by `DELIVERY-008-PM-LLM-POC-M2-GATE1-R5-REVIEW` is **held** until the environment preflight is completed and reviewed.

## 2. Preflight Design and Platform Disposition

Core approves the bounded dual-UTM preflight design and its fixed platform-disposition rule:
- If both environments `PASS`: select Ubuntu ARM64 (for product-ISA alignment).
- If ARM64 `FAIL` or `INCONCLUSIVE` and x86_64 `PASS`: select Ubuntu x86_64.
- If neither `PASS`: select neither, returning `INCONCLUSIVE` and a change request.

This avoids unverified performance assumptions and correctly defers the platform decision until exact environmental evidence is available. 

## 3. Authorizations

The LLM POC Team is **authorized** to:
- Prepare and inspect the exact LiteRT-LM v0.16.0 ARM64 and x86_64 API wheels.
- Prepare offline dependency closures and adapter/binding bundles in User-approved controlled paths.
- Return an immutable executable test request containing exact commands, operators, and raw paths for a separate execution authorization from Core.

## 4. Unchanged Boundaries and Blockers

This ACK authorizes **preparation of the preflight packet only**. 
- It does **not** authorize real execution of the dual-UTM preflight tests.
- It does **not** authorize M2 candidate execution, Gate 1 execution on actual hardware, downloading/loading models, latency measurements, or Pi Gate 2 product integration. 
- M2 remains `NOT_STARTED`. Real execution remains independently blocked pending explicit Core authorization of the returned executable test request.
