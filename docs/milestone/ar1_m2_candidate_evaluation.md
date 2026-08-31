# AR1M2: Candidate Evaluation and Pipeline Selection

Status: `NOT_STARTED`

## AR1M2A — Official Baseline Evaluation

Run eligible official pipelines and Whisper control on Pi 5 with frozen PCM,
real-time chunks, metrics, and repeats. Preserve native and wrapper results and
produce one comparative scorecard.

## AR1M2B — Bounded Adjustment and Pipeline Selection

Use development data for one-variable probes of threads, official
chunk/context/lookahead, VAD/endpoint cooperation, and at most one justified
conversion. Do not train or fine-tune. Post-process is diagnostic only. Freeze
each AR1M3 pipeline; finalist count is not capped.

M2A and M2B share tag `asr_r1_m2` after reviewed completion.
