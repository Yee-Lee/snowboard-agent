# AR1 Evaluation Specification

Status: `DRAFT FOR AR1M0 FREEZE`

Semantic and intent correctness is primary. Exact sentence correctness and
CER/WER support it. Also record English entity and code-switch accuracy, RTF,
first partial, speech-end-to-final, end-to-end final, RSS/PSS, CPU, threads,
temperature, throttling, partial revision, and N-best readiness.

No single metric automatically eliminates a candidate. All results remain
visible; Audio gives a reproducible comparison and User judges the trade-off.

Pre-recorded tests use deterministic real-time chunks. Measure first partial
from frozen speech start and final latency from frozen speech end. Report model
load, endpoint delay, decode cost, and wrapper overhead separately. Partial text
is observational only; Snowboard consumes final text.
