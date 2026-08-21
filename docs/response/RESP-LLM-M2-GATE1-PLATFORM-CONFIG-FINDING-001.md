# Gate 1 Platform-Config Identity Finding

- **Finding ID**: `M2-G1-PLATFORM-CONFIG-001`
- **Date**: 2026-08-21
- **Scope**: M2 / `G1-X86-PI-COMPAT-004`
- **Severity**: `BLOCKING`
- **Status**: `CHANGE_REQUEST_REQUIRED — NO CANDIDATE MANIFEST ISSUED`

## Evidence

1. `poc_llm/contracts/m1/strict-config.schema.json` requires exactly one `platform`, one absolute
   `runtime_path`, and one absolute `model_path`; `additionalProperties` is false.
2. `poc_llm/fixtures/gate1/candidate-v4.schema.json` permits exactly one `config` artifact and one
   `config.sha256` for a candidate/pairing revision.
3. Both the x86 and Pi Gate 1 runners bind their READY/result identity to that same
   `manifest.config.sha256`; the acquisition schema varies runtime/dependency artifacts by platform,
   but has no platform-keyed strict-config field.

## Deterministic Conflict

A strict config with `platform=ubuntu-x86_64` and x86 runtime path cannot truthfully validate as the
Pi configuration. A Pi config must differ in `platform`, runtime path and runtime checksum, therefore
has a different config checksum. The current candidate schema has no way to bind both configurations,
while both runners require the single candidate config checksum. Selecting either config makes the
other platform's strict identity unverifiable.

## Impact

- The acquired Gemma4-E2B artifacts cannot yet be used to issue a valid candidate/acquisition
  manifest.
- No real x86 pre-screen or Pi compatibility try-run may start under Packet 004.
- Replacing a config after x86 selection, reusing one platform's hash, or omitting strict validation
  would violate M1 identity and Gate 1 provenance rules.

## Required Core Decision

Issue a revised frozen Gate 1 schema/lock/runner packet that either:

1. binds `configs.ubuntu-x86_64` and `configs.pi-debian13-aarch64` independently, including each
   config path and SHA-256, and makes each runner verify its own platform config; or
2. provides another explicit identity model that preserves both platform-specific strict settings and
   immutable candidate/pairing identity.

The revision must also define how each platform-specific adapter/dependency bundle is included in the
authenticated acquisition identity. POC will not infer an exemption or alter a frozen schema.
