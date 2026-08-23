# REQUEST-LLM-POC-P9-SURROGATE-ENVELOPE-001

**Date**: 2026-08-23
**From**: Core Designer
**To**: LLM POC Team (M4b)
**Status**: `OPEN — AWAITING LLM POC RESPONSE`
**Blocks**: `DELIVERY-P9-SURROGATE-SPEC-001` (Core → Audio POC)

---

## Background

Per `DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001` §D04 and §5, Core Designer
is responsible for delivering a versioned deterministic M4b residency surrogate
to Audio POC before their WP4/S4 entry. This surrogate lets Audio POC run
M4A-P9 (co-residency resource reservation) without waiting for a real LLM
winner, while preserving the boundary that only Core Gate 3 / LLM Gate 2B
constitute the real combined acceptance.

Core cannot construct the surrogate without a LLM-provided resource envelope.
This request asks LLM POC to supply that envelope.

---

## Data requested

Please provide the following for the **Pi 5 / aarch64** target platform.
Where real Pi 5 measurements are not yet available (Gate 1 real Pi execution
still Blocked), provide a conservative estimate derived from your best
available evidence (e.g. x86 Gate 1 measurements with documented scaling
rationale), and label it clearly as an estimate.

### 1. Process identity

- Exact process name(s) and the command / entry point that represents the
  LLM runtime in its normal operating state.
- Number of child processes and threads at steady state (post-READY).

### 2. Memory envelope

- **Steady-state RSS** (MiB): memory footprint after model load and warm-up,
  before any inference request.
- **Peak RSS during inference** (MiB): maximum observed during a single
  inference call on the declared model/quantization.
- **PSS if available** (MiB): to disambiguate shared pages.
- Model identity and quantization (name, version, quantization level) that
  these numbers correspond to.
- Whether the numbers are from real Pi 5 measurement or estimated; if
  estimated, the source measurement platform and scaling method.

### 3. CPU load pattern

- CPU usage (%) at steady idle (post-READY, no request).
- CPU usage (%) at peak during inference.
- Approximate inference duration for a representative request.

### 4. Thermal and throttling observation

- Any known thermal or throttling behavior on Pi 5 during sustained inference.
- Whether the process is known to cause thermal throttle on a stock Pi 5 4GB
  under ambient conditions.

### 5. Startup and cleanup

- Approximate time from process start to READY (model loaded, ready to
  accept requests).
- Cleanup behavior: does the process release all memory and file descriptors
  cleanly on normal exit? Any known residue?

### 6. Conservative ceiling

- The number you would recommend Core use as a **conservative upper-bound
  reservation** for the surrogate, such that Audio POC results remain valid
  even if the real LLM footprint is at its worst observed level.
- Rationale for that number.

---

## What Core will do with this

Core Designer will use the above to build a `DELIVERY-P9-SURROGATE-SPEC-001`
document containing:

- a versioned, checksummed surrogate script or artifact;
- the exact RSS/thread/CPU envelope to reserve;
- a bounded startup/READY/cleanup sequence; and
- explicit PASS / FAIL / Blocked rules.

The surrogate will be delivered to Audio POC via their `docs/pm_handoff/`.
It will not simulate LLM semantic quality and cannot substitute for LLM
Gate 2B or Core Gate 3 combined acceptance.

---

## Response format

A brief written response committed to the LLM POC repo and notified to Core
with a full SHA is sufficient. Core does not require a formal delivery
document; a plain response covering the six items above is enough to unblock
surrogate construction.

---

## Urgency

Audio POC M3 qualification is now authorized to proceed (test packet pending).
M4A-P9 is on the critical path for Audio POC M4. Core needs this envelope
**before Audio POC WP4/S4 entry**, which follows M3 hardware qualification.
Early response is appreciated to avoid blocking Audio M4 entry.
