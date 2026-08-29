---
requestor: "Designer"
owner: "Developer"
status: "Resolved"
---

# CR_M4_II — M4A exact-candidate final confirmation

## Disposition

**RESOLVED — M4A Core Gate 3 is Accepted for product candidate
`6c3ba95455dc5c2a152aa230b8ae5915887fe6a9`.**

Designer reviewed only final design alignment, the telemetry correction and the
Tester reconciliation; the completed Tester matrix and Pi suite were not rerun.
The candidate is an append-only descendant of the rejected telemetry candidate,
and all changes after freeze are review/evidence documentation. `src/`, `tests/`,
`scripts/`, `native`, dependency metadata and config contracts remain byte-aligned
with the accepted candidate.

## Code and design alignment

- `offline_child_environment()` always overrides inherited
  `ORT_DISABLE_TELEMETRY` with `1`.
- ASR supervisor and TTS worker set the same invariant at module entry before
  lazy ONNX Runtime or sherpa initialization, including direct invocation.
- Conflicting-value subprocess regressions cover both direct child paths without
  weakening the full descendant syscall audit.
- The correction changes no public API, Audio Protocol schema, artifact lock,
  dependency version, engine profile or lifecycle ownership.
- The implementation design now explicitly records this production-owned launch
  invariant and closes `IR_dev_M4_I`.

## Evidence reconciliation

- Portable run `m4a-6c3ba954-20260829-t01`: CPython 3.11.16, 3.12.3 and
  3.13.15 each report 171 passed with zero fail, skip or xfail.
- Rebooted Pi run `m4a-6c3ba954-20260829-pi01`: target preflight Pass; seven
  real-device tests passed in 173.109 seconds.
- The complete descendant trace records zero IPv4/IPv6 attempts and zero
  downloader calls despite inherited `ORT_DISABLE_TELEMETRY=0`.
- ASR, TTS-to-ALSA, recovery, 20-turn resource, privacy, package and cleanup
  cards all Pass; all final cleanup counters are zero.
- The official generator validated 16 required Audio inheritance/delta rows
  against the same candidate and passing result cards.

Authoritative evidence is
`docs/outsource/evidence/M4A-TESTER-6C3BA954-20260829/`, recorded at Core commit
`90d5904399b1318a6224e1869ab3101840c140aa`. `TRDEV-M4A-005` and the Developer
design question are Resolved. M4A is Accepted and M4B may proceed.

## Milestone boundary

This is a sub-gate acceptance, not overall M4 acceptance. The shared real
M4A+M4B resource row remains Pending until an LLM input is Accepted; M4B Gate 2A,
Gate 2B/Core product work and M4C are not complete. Therefore this review does
not authorize `core_m4`, any M4 milestone tag or M5/ALPHA entry.
