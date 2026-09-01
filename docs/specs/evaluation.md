# AR1 Evaluation Specification

Status: `AUTHORITATIVE / FROZEN AT AR1M0`

Semantic and intent correctness is primary. Exact sentence correctness and
CER/WER support it. Also record English entity and code-switch accuracy, RTF,
first partial, speech-end-to-final, end-to-end final, RSS/PSS, CPU, threads,
temperature, throttling, partial revision, and N-best readiness.

No single metric automatically eliminates a candidate. All results remain
visible; Audio gives a reproducible comparison and User judges the trade-off.

Before a commit containing formal scores, rankings, hardware-result
dispositions, or qualification language is created or pushed, User must give
explicit approval. Unapproved measurements and scorecards remain drafts, must
be labeled non-formal, and must not imply qualification or acceptance.

Pre-recorded tests use deterministic real-time chunks. Measure first partial
from frozen speech start and final latency from frozen speech end. Report model
load, endpoint delay, decode cost, and wrapper overhead separately. Partial text
is observational only; Snowboard consumes final text.

Formal comparisons require a frozen candidate identity, fixture roles,
real-time chunk schedule, repeats, scorer version, normalization, endpoint
method, and resource-sampling method before results are viewed. Failed and
incomplete rows remain visible. Post-process and second-scorer observations are
diagnostic and receive no AR1M3 comparison credit.
