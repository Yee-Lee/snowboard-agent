# DELIVERY-023 — Gate 2B Memory PSI Removal

- **Date**: 2026-08-29
- **From**: LLM POC Team
- **To**: PM / Core Designer
- **Status**: `SUBMITTED — USER-DIRECTED CONTRACT ADJUSTMENT / ACK MAY FOLLOW EXECUTION`
- **Affected boundary**: M4B-P9 combined resource evidence and decision rule
- **Effective revision**: Gate 2B packet `2026-08-29-r14-user-resource-adjustment`

## User decision

The User directs the LLM POC to remove system-wide Memory Pressure Stall Information (PSI) from the
prospective Gate 2B execution surface. The runner must not read `/proc/pressure/memory`, require a
`psi=1` boot, store PSI observations, or use a PSI delta in P9/P10B disposition. Small cumulative
system-wide stall counters do not provide an actionable candidate capacity or stability decision for
this POC and caused environment/runner work without changing the combined workload conclusion.

The incoming M4b contract remains read-only. This delivery records the authorized adjustment and asks
Core to update its P9 interpretation. Core ACK may follow the already authorized Pi execution and does
not block evidence collection, but the final Gate 2 delivery must link Core's disposition.

## Exact retained P9 resource gates

Removal of PSI does not relax the remaining 4 GB acceptance boundary. Revision r14 still requires:

- `swap=0` throughout the run;
- `system_used = MemTotal - MemAvailable` no greater than 3584 MiB in every sample;
- zero OOM-kill increase;
- continuous Core/controller, VAD, ASR, TTS and LLM process-tree PSS/RSS, CPU, thread and ownership
  observations;
- predeclared leak-slope and late-versus-early memory-delta limits;
- temperature below 80 °C and `throttled=0`;
- 20 accepted combined sessions with no stale/history contamination; and
- reverse shutdown, zero process/ALSA residue and owned-log hygiene.

Sum RSS remains diagnostic and is not substituted for the system-used capacity gate. No 8 GB result,
surrogate run or diagnostic session can replace the mandatory 4 GB P9/P10B execution.

## Evidence and history boundary

This adjustment is prospective. Immutable `G2B-PI-COMBINED-001` through `005`, including Attempt 002's
missing-PSI `INCONCLUSIVE` record and later diagnostic observations, remain unchanged as execution
history. They do not become PASS and are not reused as formal credit. The next exact-SHA preflight,
single-session no-credit diagnostic and formal Attempt 006 use the r14 execution surface and fresh
run IDs/evidence roots.

## Core ACK requested

Please acknowledge in one response that Core accepts r14 P9 evaluation without Memory PSI and will
use only the retained mandatory resource, stability and cleanup gates above when reviewing the final
Gate 2B result. No runner change beyond the locked r14 removal should be requested unless a retained
gate or evidence integrity defect is identified.
