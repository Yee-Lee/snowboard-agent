# REQ-AUDIO-M3-PACKET-SIGNOFF-001

**Date**: 2026-08-23
**From**: Audio POC Team
**To**: Core Designer
**Status**: `READY FOR CORE ONE-TIME ACK / NO HARDWARE EXECUTION YET`

## One-time ACK requested

Please issue one consolidated ACK for the User-approved M3 risk-focused qualification
packet and its locally verified runner. Core is not asked to change source, add tests,
revalidate a remote branch, prepare a runner, create a sign-off JSON, operate the Pi,
or score results. Audio POC owns all remaining execution and evidence work.

The ACK advances only the M3 Pi 5/HAL entry gate. It does not report hardware results,
activate M3.1, execute the ASR fallback, approve a winner/no-go, or claim P9/Gate 2
credit.

## Immutable review identities

| Field | Exact identity |
| --- | --- |
| Packet | `M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001` |
| POC repo branch | `audio` |
| POC execution candidate SHA | `655e80ec4ed287708ed0a47f383b645d88650b18` |
| Packet manifest | `poc_audio/manifests/m3_risk_qualification_packet.json` |
| Packet manifest SHA-256 | `ebadd62016dcffe2f231d35d2bb505d76bcd67512640cf6e8e21e0ad30465c55` |
| Core HAL execution SHA | `ff09199583644a8f0822153e371589f52ae821a0` |
| Core HAL delivery | `DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-002` |
| Core P9 surrogate ACK SHA | `caf4f7ba867e4ebc1972df0ade86c605a873a286` |

The submitted POC candidate SHA is immutable. Later Audio documentation commits do
not replace it as the formal execution identity.

## Local verification completed

- `bash poc_audio/tools/run_m3_qualification.sh validate` — `PASS`.
- `PYTHONPATH=poc_audio/src python3 -m unittest discover -s poc_audio/tests -p
  'test_*.py'` — 176 tests passed.
- Focused M3 packet/HAL suite — 26 tests passed.
- Python compile, shell syntax and changed-line whitespace validation completed.
- No Pi hardware result or candidate disposition was produced.

The runner binds the exact Core SHA and direct `hw:` devices; forces controlled
evidence/private PCM outside Git; rejects dirty or mismatched POC/Core checkouts;
uses Core AudioOutput for 16 kHz mono S16_LE to 48 kHz stereo S32_LE adaptation;
enforces a disabled network namespace for every candidate inference; covers the ten
fixed captures, paired direct/HAL ASR fixture lock, six TTS prompts and LIFE-01–06;
and requires a complete 22-result draft summary before review.

## Complete ACK scope

One ACK confirms all of the following, with no separate follow-up ACK required:

1. POC execution is fixed to
   `655e80ec4ed287708ed0a47f383b645d88650b18`.
2. The reviewed packet manifest SHA-256 is
   `ebadd62016dcffe2f231d35d2bb505d76bcd67512640cf6e8e21e0ad30465c55`.
3. Formal HAL execution is fixed to Core
   `ff09199583644a8f0822153e371589f52ae821a0`.
4. Audio may begin the packet's formal Pi execution; all gates, stop rules, User
   publication confirmation and M3.1 boundaries remain unchanged.
5. Core P9 corrected ACK is already committed at
   `caf4f7ba867e4ebc1972df0ade86c605a873a286`; no further P9 input is requested.
   P9 remains outside this 22-result start packet and does not block M3 execution.

Please commit exactly one response named `RESP-AUDIO-M3-PACKET-SIGNOFF-001.md` with
status `ACKNOWLEDGED — FORMAL PI EXECUTION AUTHORIZED`, the packet/POC/Core identities
above and the unchanged boundary statements.
No Core-generated JSON is requested. After intake, Audio will use the committed ACK
SHA to create the controlled, non-Git sign-off document required by the runner:

```json
{
  "schema_version": "1.0",
  "status": "CORE_PACKET_SIGNED_OFF",
  "packet_id": "M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001",
  "response_id": "RESP-AUDIO-M3-PACKET-SIGNOFF-001",
  "poc_execution_sha": "655e80ec4ed287708ed0a47f383b645d88650b18",
  "core_execution_sha": "ff09199583644a8f0822153e371589f52ae821a0",
  "core_acceptance_sha": "<RESP-AUDIO-M3-PACKET-SIGNOFF-001 commit SHA>",
  "packet_manifest_sha256": "ebadd62016dcffe2f231d35d2bb505d76bcd67512640cf6e8e21e0ad30465c55"
}
```

The sign-off JSON remains in the controlled store, not Git. Formal Pi qualification
will remain stopped until the single ACK is committed and the Audio-created JSON
passes the runner authorization guard. If Core cannot issue the ACK, return one
consolidated response containing every blocking finding and its exact packet section;
do not split findings across iterative handoffs.

The immutable candidate manifest records the P9 intake state that existed when
`655e80e...` was cut. Core's later `caf4f7b...` ACK closes that external prerequisite
without changing the candidate source, packet gates or 22-result set. The exact P9
artifact was already vendored and checksum-verified in the candidate; Audio owns its
subsequent bounded execution and does not need another Core response.

## Responsibilities after ACK

Audio POC will independently perform checkout/clean checks, Pi preflight, ten fixed
captures, paired VAD/ASR paths, TTS playback/listening, LIFE-01–06, offline execution,
cleanup/resource/thermal evidence, the 22-result draft summary and User confirmation.
Core's next decision point is Gate 2A result intake, not intermediate test operation.
