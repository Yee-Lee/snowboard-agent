# Gate 1 M2 ARM64 Preflight Diagnostic ACK

- **Record ID**: `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **In response to**: `DELIVERY-010-PM-LLM-POC-M2-ARM64-PREFLIGHT-DIAGNOSTIC-REVIEW`
- **From**: Core Team Designer
- **To**: LLM POC Team via PM
- **Status**: `DESIGNER APPROVED — EXCEPTION ACCEPTED & BOUNDED CONTINUATION AUTHORIZED`
- **Date**: 2026-08-22

## 1. Exception Acceptance

Core has reviewed the provided target SHA `265db05776b6bf5fadca5b3c3ab41345aa68819e`.
We formally accept this exact review target as the complete sanitized ARM64 diagnostic and change record. Core explicitly waives the missing pre-execution Core authorization, the exhausted rerun budget, and baseline deviations for this specific instance. The diagnostic `PASS` is accepted as the formal ARM64 environment-preflight result, and no further corrective ARM64 rerun is required for this stage.

## 2. Revised Platform Disposition

The dual-UTM disposition is hereby revised: the accepted ARM64 `PASS` is sufficient to select ARM64 as the primary Ubuntu pre-screen track. The x86_64 environment remains an independent portability/fallback track and does not block ARM64 progress.

## 3. Workflow Authorization

Core authorizes the bounded ARM64 and x86_64 WIP branch workflow. The branch owners are authorized to proceed through completion of their approved workstation scopes—including append-only runner/lock/config/adapter refinement, controlled artifact preparation, and immutable Ubuntu candidate pre-screen execution under predeclared commands and stop conditions—without requiring a new Core round trip for every preparation step. 

## 4. Integration Boundary

A reviewed, sanitized integration commit may be merged back to the `llm` branch **only after** both branch owners report their results and the Technical Lead confirms the merge boundary. The integration must not merge binaries, raw logs, private paths, credentials, or host identities.

## 5. Unchanged Boundaries

M2 remains `NOT_STARTED`. R5 exact-SHA acceptance remains held. This authorization permits only the bounded pre-screen executions on the designated UTM workstations. It does not authorize Pi access, Gate 2 evidence generation, product finalist selection, or product integration.
