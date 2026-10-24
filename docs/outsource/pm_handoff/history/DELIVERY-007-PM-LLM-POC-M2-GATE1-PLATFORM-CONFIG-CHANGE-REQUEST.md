# LLM POC Gate 1 Platform-Config Identity Change Request

- **Delivery ID**: `DELIVERY-007-PM-LLM-POC-M2-GATE1-PLATFORM-CONFIG-CHANGE-REQUEST`
- **From / via**: LLM POC Team / User-authorized Agent courier via PM
- **To**: Core Team Designer
- **Affected contract**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Affected accepted packet**: `G1-X86-PI-COMPAT-004` / `DELIVERY-LLM-POC-M4B-GATE1-PACKET-R4-ACK-001`
- **Finding**: `M2-G1-PLATFORM-CONFIG-001`
- **Status**: `CORE DECISION REQUESTED — M2 ENTRY / GATE 1 EXECUTION BLOCKED`
- **Architecture change**: `No`
- **Date**: 2026-08-21

## Decision Requested

Please issue a revised, immutable Gate 1 schema/lock/runner packet that can authenticate the two
required strict platform configurations for one logical candidate identity:

- Ubuntu 24.04 x86_64 full pre-screen; and
- product Debian 13 aarch64 Pi compatibility try-run.

The replacement must preserve the existing immutable candidate ID, pairing revision, two-stage
selection, maximum-two Pi preselection, no-backfill and Gate 1-to-Gate 2 non-inheritance rules.

## Reproducible Finding

`poc_llm/contracts/m1/strict-config.schema.json` requires a strict config to declare exactly one
`platform`, one absolute `runtime_path`, one absolute `model_path`, and their platform-specific
checksums. `poc_llm/fixtures/gate1/candidate-v4.schema.json` permits only one `config` artifact and
one `config.sha256` for a candidate/pairing revision. Both revision-004 runners authenticate their
READY/result identity against that single candidate config checksum.

Consequently, an x86 strict config cannot truthfully validate the Pi runtime path/checksum/platform,
and a Pi strict config cannot truthfully validate the x86 values. Selecting either config means the
other required platform has no authenticated strict configuration. The current acquisition schema
varies runtime/dependency artifacts by platform but has no matching platform-keyed config binding.

## Required Revision Properties

The preferred resolution is a platform-keyed candidate configuration identity, for example:

1. independently authenticated `configs.ubuntu-x86_64` and `configs.pi-debian13-aarch64` entries,
   each with its strict config path and SHA-256;
2. runner verification of the config matching its own platform, including READY identity;
3. authenticated inclusion of each platform's adapter/dependency bundle in acquisition identity; and
4. deterministic negative regressions for swapped config, wrong config hash, wrong runtime path and
   cross-platform READY identity.

Core may choose an equivalent representation, but it must retain strict platform identity and be
reviewable before any real candidate evidence is produced.

## Scope and Current Disposition

This request does not ask for Gate 2A, product integration, a model baseline decision, or a change to
the accepted candidate-selection policy. The POC Team has acquired and checksum-verified only the
first proposed candidate's controlled artifacts; this acquisition is not candidate, hardware or
finalist evidence. No candidate manifest has been issued and no real x86 or Pi Gate 1 run has begun.

Until Core accepts a replacement packet, M2 remains `PLANNED / BLOCKED` and the only allowed work is
controlled acquisition and repository-only preparation.
