# CR-AUDIO-PI-PRODUCT-CONTRACT-001

- Date: 2026-09-06
- From: Audio POC Team
- To: Core
- Related status: `PI-MIGRATION-STATUS-001`
- Status: `BLOCKING CROSS-TEAM PRODUCT CONTRACT DECISION REQUIRED`

## Conflict

Audio's revised formal runner fails closed unless one read-only M4A product has
an `.audio-poc-product.json` identity marker, a hashed file-level product
manifest, complete runtime/native inventories, and hash-keyed model object
markers. The qualification entry point currently expects the same product
layout.

Core's existing `scripts/m4a_audio_product.py` materializes the accepted product
with `install-manifest.json` schema `sbd.m4a.product-install.v4`. Its runtime and
artifact layout and its aggregate inventory fields do not directly satisfy the
new Audio marker, file inventory, or hash-keyed model layout. Therefore the
future canonical product cannot yet pass the Audio preflight without an
unreviewed conversion or duplicate product tree.

No product has been materialized or copied during this inspection.

## Requested Core decision

1. Name the canonical M4A product schema and directory layout that both Core
   activation and Audio formal/qualification runners must consume.
2. Either extend Core materialization to emit the complete Audio-verifiable
   file inventory and object identities in place, or authorize a deterministic
   read-only adapter manifest over the existing install without copying runtime,
   models, native binaries, or virtual environments.
3. Define the single authoritative product ID/digest and the exact relationship
   between it and `sbd.m4a.product-install.v4`.
4. Add a bounded integration preflight proving that Core's materialized product
   is accepted by Audio validation before any benchmark or activation.

## Preserved boundary

This request does not authorize product materialization, model/runtime copying,
benchmark execution, service activation, hold movement, cleanup, commit, or
push. Until Core resolves the contract, Audio will preserve both implementations
and will not weaken its feedback-driven integrity checks.
