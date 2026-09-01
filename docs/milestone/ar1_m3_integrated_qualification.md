# AR1M3: Integrated Product Qualification

Status: `NOT_STARTED`

AR1M3 integrated product qualification is Pi 5-only. The workstation may run
the same contracts with fake or controlled development inputs to diagnose the
harness, but such runs receive no qualification credit and cannot replace any
Pi fixture, lifecycle, resource, offline, or target-microphone evidence.

Test each frozen pipeline with its best validated VAD/endpoint. Compare with
Whisper base-Q8 and its accepted Silero control. Exclude post-process and second
scorer.

Use untouched holdout and Pi 5 target-microphone sessions. Record quality,
streaming latency/stability, resources, offline behavior, persistent sessions,
cancel, timeout, error, recovery, reset, and cleanup. User performs blind-first
transcript review followed by live review. Fixes require a new SHA and rerun.

## Target-microphone collection gate

After every AR1M3 pipeline is frozen, freeze the target-microphone prompts,
speaker/session plan, Pi 5 hardware identity, microphone identity and placement,
room/noise conditions, capture format, repeats, authorization, and cleanup
procedure. Only then collect the target-microphone qualification sessions.

These sessions are qualification-only: they cannot tune a model, endpoint,
adapter, normalization, scorer, or fixture method, and they cannot influence
AR1M2 selection. Store raw audio and sensitive transcripts outside Git; commit
only controlled identities and reviewed sanitized evidence. Review transcripts
blind-first, then conduct the frozen live review. A capture-method defect makes
the affected evidence `INCONCLUSIVE` until a reviewed new packet and complete
rerun; it never permits selective recollection after seeing scores.
