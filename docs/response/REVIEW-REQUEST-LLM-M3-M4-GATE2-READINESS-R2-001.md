# REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R2-001

- **Date**: 2026-08-28
- **From**: LLM POC Designer / Technical Lead
- **To**: Independent Reviewer
- **Status**: `REPLACEMENT IMPLEMENTED / TARGETED RE-REVIEW REQUIRED / PI NOT AUTHORIZED`
- **Reviewed base**: `0638f5ad859627014f7cf0d57882ac394b100466`
- **Gate 2A replacement lock**: `6b5aa1cad7572cd38304778e2d0a90f30061848727b59db6ddb5b27498c9a4e3`
- **Gate 2B replacement lock**: `05c5adfca9d10c3d383a7db51dd2ccfd84d281f8b1b293f33a0e6324f5cad0a1`
- **Source commit**: pending User-authorized milestone commit; no Pi execution may start

## Finding closure map

### F1 — independently fail-closed PASS evidence

`verify_gate2a_result()` and `verify_gate2b_result()` independently recompute claimed P-item
dispositions. Gate 2B re-verifies the bound Gate 2A result rather than trusting its top-level PASS.
Both schemas now require concrete sample, metric, marker, owner, cleanup and log-scan fields.
Negative tests mutate case identity/count, P2/P3/P8 flags, P4 metrics, P5 markers,
session/request correlation, owner data and cleanup proof; each mutation is rejected.

### F2 — result error categories

The shared `gate2_errors_v1.py` defines `CandidateViolation`, `EnvironmentInvalid`,
`EvidenceInvalid`, `PacketDefect` and `CleanupViolation`. Only candidate and cleanup violations map
to FAIL. Probe, sampler, filesystem, evidence, packet and protocol-I/O failures map to
INCONCLUSIVE with sanitized category/type evidence. P2/P4/P5/P8 no longer turn observation
exceptions into candidate FAIL. The error matrix and thermal/PSI/sampler/evidence-write injections
exercise each class.

### F3 — P10B leak and bounded all-domain cleanup

The sampler captures one ordered stable point after every session. It applies the frozen P10A
sessions 6–20 slope limit of 4.0 MiB/session and sessions 16–20 versus 1–5 median-delta limit of
64 MiB to combined PSS and system-used, retaining per-owner PSS diagnostics. A 5 MiB/session leak
fails below the capacity ceiling. The coordinator preserves every started root, attempts all four
reverse stops, applies bounded owner-group fallback, and records per-domain proof. Injected stop
failure for VAD, ASR, TTS and LLM leaves every owned group absent and produces non-PASS.

### F4 — P5 chunk-boundary race

The P5 backend now uses lock-protected `STARTING_CHUNK`, `ACTIVE_CHUNK` and `BETWEEN_CHUNKS`
transitions. `ACTIVE_CHUNK_CANCEL` requires exactly one native cancel; `BETWEEN_CHUNKS_STOP`
requires zero native cancels and atomically prevents continuation. Both require the same fixed
TIMEOUT window, same-child health, rebuild and cleanup. A deterministic barrier test controls the
post-close/pre-next-chunk schedule.

### F5 — data-dependent log hygiene

Gate 2A scans static forbidden strings plus current catalog text, P5 input and P8 nonce/trap
canaries. Gate 2B scans its controller/LLM-owned files using current in-memory transcript,
nonce/trap and speech canaries. Evidence retains only file hashes, counts and disposition. Tests
prove a current P8 or Gate 2B canary leak is detected without persisting the matched string.

## Verification

```text
python3 -m unittest discover -s poc_llm/tests/gate2 -p 'test_*.py'
Ran 49 tests — OK
```

The Gate 1 136-test regression and final bytecode/diff checks must be rerun after the exact
replacement commit is assigned. This response does not claim hardware credit or authorize Pi use.

## Requested targeted decision

Confirm that F1–F5 are closed without reopening the explicitly excluded artifact-adversary, Audio
quality, semantic-oracle, product-composition or cumulative-allocation topics. Approval authorizes
the previously agreed sequence: milestone commit, Gate 2A Pi execution, User review, then Gate 2B.
