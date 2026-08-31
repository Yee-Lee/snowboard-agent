# AR1 Streaming Protocol Specification

Status: `DRAFT FOR AR1M0 FREEZE`

The POC contract supports model load, session create/reset, timestamped PCM
chunks, partial events, input-finished, final event, typed error, cancel, and
bounded shutdown. Models stay resident and utterance state is isolated. Partial
text is observable but only final text reaches downstream product logic.

VAD/endpoint control is candidate-specific and its timing remains separate. A
fake scorer may prove final/N-best fallback and cancellation, but no real scorer
enters AR1M3.
