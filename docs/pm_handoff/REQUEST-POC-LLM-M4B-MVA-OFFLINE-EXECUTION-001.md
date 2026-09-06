# REQUEST-POC-LLM-M4B-MVA-OFFLINE-EXECUTION-001

- Date: 2026-09-06
- From: Core
- Owner: LLM operator CLI
- Status: `AUTHORIZED — EXECUTE AND REPORT`
- Execution commit: `ac25aa1`
- Surface SHA-256: `f774c8d018445b91bef4fa3b59bcc4f288d6699deb1fd09a2cb9baf8f2ddc461`

## User direction

The User assigned the remaining offline M4B-MVA execution to the separate LLM
operator CLI. Core must not execute or impersonate the LLM measurement. The LLM
operator owns the target run, durable evidence, cleanup, result review, and any
append-only result commit.

## Accepted migration receipt

- The Pi canonical LLM worktree is clean at `ac25aa1`.
- `PI_PROD_PRODUCTS/m4b/current` resolves to product `8279e79`.
- Product profile, schema, runtime manifest, native library, model, and wheel
  identities passed the bounded verifier.
- Product and artifact payloads use independent read-only inodes; the product has
  no symlinks.
- The Phase 1 private evidence bundle is verified outside the Pi. Its legacy 36
  run directories and temporary export tree have been removed.
- Workspace preflight and frozen-surface verification passed. No MVA target case
  has run yet.

## Required execution

1. Re-read the current packet at
   `poc_llm/tests/mva/M4B-MVA-POC-PACKET-001.md`; use its order and stop rules
   exactly.
2. Confirm the full `ac25aa1` commit and the surface digest above. Use the private
   config bound to `PI_PROD_PRODUCTS/m4b/8279e79`, `PI_ARTIFACT_STORE`, and the
   assigned LLM run, evidence-export, and cache roots.
3. Establish the packet's offline condition through a local console or an
   operator-controlled one-shot job. If a one-shot job is used, it must stop
   `wlan0`, run as the service operator, preserve stdout/status in the assigned
   evidence root, and restore networking on success, failure, signal, or timeout.
4. Run `prepare-install`, retain its private receipt, then execute only the next
   ordered MVA case. Do not skip, retry, or backfill a failed/incomplete case.
5. Continue the packet through its required reboot/case matrix only while every
   stop gate passes. A failed gate stops later cases and preserves evidence.
6. Return exact case results, ledger/summary identities, cleanup proof, remaining
   gaps, and a complete append-only commit proposal. Commit and push final team
   work as the User directed; do not amend or move either published candidate.

The private config, receipt, prompts, answers, raw evidence, host locator, and
physical home paths must remain outside Git. Git documents use only logical
locators and sanitized result identities.

