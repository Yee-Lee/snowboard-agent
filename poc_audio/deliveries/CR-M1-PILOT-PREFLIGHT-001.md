# CR-M1-PILOT-PREFLIGHT-001 — Controlled Pilot ASR Preflight

Status: `USER/DESIGNER APPROVED`  
Date: 2026-08-09  
Decision owner: User / Designer

## Trigger and delivery impact

The completed, reviewed 40-item Pilot can reveal an unusable native-to-ASR
preparation path before Formal collection finishes. This advances reproducible
fixture preparation and ASR-wrapper readiness; it does not close the fixture
gate, select a candidate, or advance M2.

## Approved bounded exception

ASR implementations may consume the complete Pilot only after its preparation
manifest validates all 40 files. Every result is an `OBSERVATION`, recording
source SHA, candidate/artifact identity, conversion configuration, command,
timing, cleanup and sanitized summary.

An observation may guide M1 development or trigger a new change request. It
must not produce `advance`, `reject`, `winner`, frozen quality evidence, or a
M2 status change.

## Fixed boundaries

- Native Pilot WAVs remain immutable, local, and Git-ignored.
- The preflight selects native channel 0 and derives 16 kHz mono S16_LE with
  `m1-pilot-asr-preflight-v1`.
- Temporary +12 dB monitoring gain is excluded.
- Derived files and results remain Git-ignored; only sanitized evidence is tracked.
- This diagnostic preparation is not the final Core M3 AudioInput adaptation.
- Formal 100-item completion, catalog/metric review, and the frozen gate remain
  required for comparison and decisions.

## Risk

Pilot has only 20 speech references, so it cannot satisfy the approved ASR
quality gate. If capture topology, channel policy, or preparation changes,
preserve this revision locally and create a new one; never merge result sets.
