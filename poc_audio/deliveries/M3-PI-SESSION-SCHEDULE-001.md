# M3-PI-SESSION-SCHEDULE-001

**Recorded**: 2026-08-23
**Scheduled date**: 2026-08-24
**Status**: `SCHEDULED / NOT EXECUTED`

## Scope

The User deferred the authorized M3 Raspberry Pi 5 qualification session to
2026-08-24. No Pi connection, capture, playback, candidate inference, hardware
result or disposition was produced on 2026-08-23.

Reserve one continuous three-hour Pi session with a four-hour scheduling buffer.
Expected User/operator participation is 30–45 minutes for spoken captures,
impact/cough/playback stimuli and the six-prompt TTS listening review.

## Fixed execution identities

| Field | Identity |
| --- | --- |
| POC execution candidate | `655e80ec4ed287708ed0a47f383b645d88650b18` |
| Packet manifest SHA-256 | `ebadd62016dcffe2f231d35d2bb505d76bcd67512640cf6e8e21e0ad30465c55` |
| Core HAL execution SHA | `ff09199583644a8f0822153e371589f52ae821a0` |
| Core packet ACK commit | `e63884451368079a9c876c2994c982627aa7d766` |
| Core P9 ACK commit | `caf4f7ba867e4ebc1972df0ade86c605a873a286` |
| Direct ALSA baseline | input/output `hw:0,0`; input channel `0` |

The controlled sign-off document was generated outside Git and passed the local
schema guard. Its content must be regenerated or transferred to the controlled Pi
store if the temporary workstation copy is unavailable tomorrow; the identities
above must not change.

## Tomorrow's entry sequence

1. Receive the operator-managed SSH config path, alias, Pi Audio POC checkout path
   and Pi Core checkout path without recording endpoints or credentials in Git.
2. Check out clean POC `655e80e...` and Core `ff09199...` worktrees.
3. Run the read-only environment check and formal packet authorization guard.
4. Run M3 preflight. Begin capture only if preflight passes.

Any identity mismatch, dirty checkout, device owner, malformed artifact or failed
preflight stops the session. It does not authorize an ad hoc fix, parameter change,
fallback activation or M3.1.
