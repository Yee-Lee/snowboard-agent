# AR1M3: Integrated Product Qualification

Status: `NOT_STARTED`

Test each frozen pipeline with its best validated VAD/endpoint. Compare with
Whisper base-Q8 and its accepted Silero control. Exclude post-process and second
scorer.

Use untouched holdout and Pi 5 target-microphone sessions. Record quality,
streaming latency/stability, resources, offline behavior, persistent sessions,
cancel, timeout, error, recovery, reset, and cleanup. User performs blind-first
transcript review followed by live review. Fixes require a new SHA and rerun.
