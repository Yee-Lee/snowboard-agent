# AR1 Streaming Protocol Specification

Status: `AUTHORITATIVE / FROZEN AT AR1M0`

The POC contract supports model load, session create/reset, timestamped PCM
chunks, partial events, input-finished, final event, typed error, cancel, and
bounded shutdown. Models stay resident and utterance state is isolated. Partial
text is observable but only final text reaches downstream product logic.

VAD/endpoint control is candidate-specific and its timing remains separate. A
fake scorer may prove final/N-best fallback and cancellation, but no real scorer
enters AR1M3.

## AR1M0 wire contracts

- `asr_r1/schemas/lifecycle_command.schema.json` fixes lifecycle operations.
- `asr_r1/schemas/pcm_chunk.schema.json` fixes ordered, timestamped 16 kHz mono
  S16_LE input chunks.
- `asr_r1/schemas/streaming_event.schema.json` fixes partial, final, N-best,
  and typed-error result events.

Within one session, chunk and event sequence numbers are contiguous and chunk
timestamps strictly increase. `input_finished` is accepted only after PCM;
cancel and final are terminal until reset. Reset clears utterance state without
unloading the resident model. Shutdown has a caller-supplied positive bound and
must release every session. The dependency-free fake runtime in
`asr_r1/fake_runtime.py` is the AR1M0 executable reference for these invariants,
not evidence about a real engine.
