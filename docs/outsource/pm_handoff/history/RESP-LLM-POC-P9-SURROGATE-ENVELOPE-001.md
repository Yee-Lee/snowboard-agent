# RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001

**Date**: 2026-08-23
**From**: LLM POC Team (M4b)
**To**: Core Designer
**In response to**: `REQUEST-LLM-POC-P9-SURROGATE-ENVELOPE-001`
**Status**: `SUBMITTED — USER APPROVED`
**Evidence baseline**: `llm` / `0d6f139470fe4ec1ad32bd8324881a45eefe601c`

---

## Scope and evidence classification

No Raspberry Pi 5 LLM measurement or Gate 2B combined run is available. The values below use the
best available model-backed evidence from Ubuntu 24.04 ARM64 UTM and are conservative Pi-surrogate
planning inputs, not Pi measurements. They cannot produce M4B-P9, M4B-P10B, Gate 2B or winner
acceptance credit.

The source record is
`poc_llm/evidence/gate1/arm64-candidate-preparation-001.json`. The two compared candidates remain
proposed Pi inputs pending Core disposition of
`DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION`; neither is a Gate 1 finalist.

## 1. Process identity

- **Observed process topology**: one isolated `python3` child in a dedicated process group. No
  additional child process is intended by the reference adapter.
- **Reference entry point**:
  `env PYTHONPATH=<authenticated-install> python3 poc_llm/harness/litert_lm_child_adapter.py
  --config <authenticated-candidate-config> --config-sha256 <sha256>`.
- **Reference adapter SHA-256**:
  `d17c225a8d358275e6ce2b992f670ba7d8d73e35d73dc3da32b3a20a574f27ff`.
- **CPU configuration**: both candidate configs request four LiteRT-LM/XNNPACK inference threads.
- **Observed post-READY thread count**: not captured. Core should treat four CPU worker slots as a
  surrogate reservation, not as a measured Linux thread count.

Pi paths and config hashes must be rebound by a future authorized Pi packet. The UTM `/tmp` paths
must not be copied into the Core surrogate or onto the Pi.

## 2. Memory envelope

| Candidate | Runtime/model identity | ARM64 UTM peak process RSS | Steady RSS | PSS |
| --- | --- | ---: | --- | --- |
| `CAND-LRT-G4E2B-MOBILE-R1` | LiteRT-LM v0.16.0; Gemma 4 E2B mobile `.litertlm`; embedded mobile 2/4/8-bit mixture | `2,072,316 KiB` = `2023.7 MiB` | not measured | not measured |
| `CAND-LRT-Q25-15B-Q8-R1` | LiteRT-LM v0.16.0; Qwen2.5 1.5B `.litertlm`; Q8 dynamic INT8 family | `2,052,192 KiB` = `2004.1 MiB` | not measured | not measured |

These are process RSS peaks from the frozen 128-input-token / 16-output-token P4 workload on ARM64
UTM. No cross-platform multiplier is claimed. For surrogate planning, the observed maximum is
rounded upward and given an additional `280.3 MiB` (`13.8%`) margin.

## 3. CPU load pattern and request duration

- **Steady-idle CPU**: not measured.
- **Peak CPU**: not measured. The declared runtime configuration is four inference threads; Core may
  synthetically reserve up to `400%` CPU as a conservative four-core load, but must label this as a
  surrogate setting rather than an observed Pi or UTM percentage.
- **Observed ARM64 UTM request envelope**: 128 input tokens, maximum 16 output tokens, temperature 0.
- **Gemma hot wall time P50/P95**: `1025.415 / 1063.333 ms`.
- **Qwen 1.5B hot wall time P50/P95**: `1703.930 / 1920.652 ms`.
- **Long-prompt maximum observed wall time**: Gemma `2220.974 ms`; Qwen 1.5B `2764.336 ms`.

No 200-input-token / 64-output-token Pi duration has been measured. For surrogate scheduling only,
linear prefill scaling plus the slower observed decode rate gives approximately `3.4 seconds` for
Gemma and `5.1 seconds` for Qwen 1.5B on ARM64 UTM. These are planning estimates, not Pi predictions.
A deterministic surrogate should round the slower estimate upward to `6 seconds` per simulated
inference, independently from its CPU and memory reservation phases.

## 4. Thermal and throttling

ARM64 UTM cannot establish Raspberry Pi temperature or throttling behavior. Stock Pi 5 4GB thermal
behavior is therefore **unknown**, including whether sustained inference throttles under ambient
conditions. Core may create a four-core synthetic CPU-pressure phase for Audio resilience testing,
but it must not label that result as LLM Pi thermal evidence or M4B-P9/P10B acceptance.

## 5. Startup and cleanup

- **Observed model-backed rebuild to READY**: Gemma `5727.829 ms`; Qwen 1.5B `4081.878 ms`.
- **Recommended surrogate startup delay**: `6 seconds`, with the protocol-level READY timeout kept
  at the contract boundary of `10 seconds`.
- **Observed cleanup**: P7 sent `SIGTERM`, performed bounded wait/waitpid, did not require `SIGKILL`,
  proved the process group absent, rebuilt the resource, and reached READY for both candidates.
  P5 workaround and P8 runs also recorded cleanup `PASS`.
- **Limit of evidence**: no separate steady-state file-descriptor census was captured. The evidence
  proves bounded process-group cleanup and no owned process residue, not an independent FD-count
  assertion.

## 6. Conservative surrogate ceiling

Core should use the following deterministic upper-bound reservation:

| Resource | Recommended surrogate setting | Classification |
| --- | ---: | --- |
| Process RSS | **2304 MiB** | estimate derived from `2023.7 MiB` maximum ARM64 UTM RSS plus `280.3 MiB` margin |
| Memory residency | **allocate, touch and hold 2304 MiB from READY through shutdown** | conservative replacement for unavailable steady-RSS evidence |
| CPU | **4 cores / up to 400% synthetic load** | configuration-derived reservation; CPU percentage not measured |
| Startup delay | **6 seconds** | rounded above the `5727.829 ms` maximum observed rebuild-to-READY |
| Inference load phase | **6 seconds** | rounded above the `5.1 second` planning estimate for 200 input / 64 output tokens |
| Child processes | **1** | reference adapter topology |

The surrogate must still measure the full target system using the M4B-P9 primary capacity metric
`system_used = MemTotal - MemAvailable`; process RSS is only the deterministic reservation input.
It must not convert surrogate success into LLM P9/P10B PASS. Real Gate 2B remains blocked until Core
records the Accepted M4a Audio final handoff and an authorized Pi 5 4GB, `swap=0` combined packet
executes successfully.

## Requested Core action

Please use this envelope to produce the versioned, checksummed
`DELIVERY-P9-SURROGATE-SPEC-001` for Audio POC. Please preserve every estimate/measurement label,
the touched `2304 MiB` lifetime reservation, four-core synthetic ceiling, bounded READY/cleanup
sequence and the explicit no-Gate-2-credit rule. No LLM candidate or winner approval is requested
by this response.
