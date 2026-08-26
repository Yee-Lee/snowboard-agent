# GATE2B-PI-PACKET-001 — Cumulative Audio + LLM Final Validation

- **Packet ID**: `G2B-PI-COMBINED-001`
- **Revision**: `2026-08-26-r1`
- **Status**: `DESIGN COMPLETE / REVIEWER CHECK REQUIRED / BLOCKED ON ACCEPTED AUDIO`
- **Entry receipts**: accepted Gate 1 cumulative receipt, accepted Gate 2A receipt, accepted Audio handoff
- **Formal credit executed here**: M4B-P9, P10B
- **Outcome ceiling**: final POC winner recommendation; Core decides

## 1. No broad regression rule

Gate 2B does not automatically rerun P1～P8/P10A/P11/P12. It authenticates their manifest chain and
the exact candidate/runtime/model/config/protocol/fixture/source identities. Only a component or
boundary changed by combined integration triggers a focused, predeclared affected-item regression.
Unchanged accepted evidence remains valid.

The surrogate P9 envelope is planning/debug input only. Formal P9/P10B requires the Core-recorded
Accepted Audio POC handoff ID, full SHA and executable kit.

## 2. Single combined execution

P9 and P10B share one 4GB `swap=0` offline execution so Audio and LLM models are not loaded twice.
The controller starts the real Core parent boundary, accepted ASR/TTS components and the accepted LLM
child, then performs:

1. authenticated idle and simultaneous-residency samples before the first session;
2. twenty frozen ASR-fixture→LLM→TTS sessions at five-second cadence;
3. per-session end-to-end and LLM timings, schema disposition, `MemTotal-MemAvailable`, full process-
   tree PSS/RSS, CPU, threads/process ownership, temperature, throttling and PSI;
4. the predeclared combined fault schedule only where Audio/LLM interaction changes an accepted
   boundary; and
5. reverse-order shutdown, waitpid and zero owner/process residue followed by the offline proof.

## 3. P9 and P10B decisions

P9 `PASS` requires every 4GB sample to keep system-used memory <=3584 MiB, `swap=0`, no OOM, no
increase in full memory-pressure stall, complete process ownership and valid cleanup. Sum RSS is
diagnostic only. An optional 8GB run uses the identical configuration and cannot repair 4GB failure.

P10B `PASS` requires 20/20 combined sessions, accepted Audio semantics, valid LLM product results,
temperature <80°C, `throttled=0x0`, no crash/leak/stale result/history contamination and final zero
residue. No sample is removed and no post-result threshold change is allowed.

## 4. Final cumulative decision

The final manifest links:

- Gate 1: P1/P6/P7/P10A/P11/P12;
- Gate 2A: P2/P3/P4/P5/P8; and
- Gate 2B: P9/P10B.

Only after all mandatory items and any P4 written disposition are accepted may the User approve a
winner proposal for Core. The POC state remains `Ready for internal review` until Core issues the
final winner ACK.

## 5. Reviewer and execution gate

The executable revision must bind the Accepted Audio receipt schema, combined process manifest,
fixtures, runner, calculations, result schema and checksums. Reviewer approval is required before
commit/push or any combined Pi run.
