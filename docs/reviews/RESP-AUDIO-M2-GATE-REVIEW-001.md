# RESP-AUDIO-M2-GATE-REVIEW-001

**Date**: 2026-08-23
**Role**: Reviewer
**Target**: `REQ-AUDIO-M2-GATE-REVIEW-001`

## 1. Dispositions by Track

| Track | Disposition | Reviewer Notes |
| --- | --- | --- |
| **ASR** | `ACCEPTED` | The proposed base Q8 primary and small Q8 fallback (P0 + greedy + fixed domain prompt) are accepted for M3 integration. Retaining the disclosed Common Voice `+1 edit` regression as a trade-off is the correct approach. (Post-ASR lexicon correction will be deferred to M4 delivery §7 as a productization recommendation). |
| **TTS** | `ACCEPTED (for M3)` | Matcha 1.13.5 is approved to advance to M3 technical validation based on the passed risk-focused evidence. The legal lineage issue is acknowledged as blocking for M4 final delivery/redistribution, but it does not block M3 technical integration. |
| **VAD** | `BLOCKED` | Execution of WebRTC 2.0.10 and Silero 6.2.1 is hereby explicitly authorized based on the User ACK. However, M2 cannot close until the VAD execution is complete and the bounded scorecard is reviewed. VAD evaluation firmly remains inside M2. |
| **M3 Entry** | `NOT_READY` | Awaiting M2 VAD closure. Before M3 entry, the exact pinned Audio HAL SHA, hardware topology (Pi 5 + INMP441 + MAX98357A), and integration retest packet must be explicitly locked. |

## 2. Findings

| Finding ID | Track | Classification | Description | Required to Close |
| --- | --- | --- | --- | --- |
| `FND-M2-001` | VAD | `BLOCKING` | VAD rows are authorized but unexecuted. M2 lacks a VAD finalist or no-go decision. | Complete bounded execution of WebRTC (and Silero if triggered) on M1 frozen labels. Submit scorecard with recall, latency, RSS, and cleanup proof. |
| `FND-M2-002` | M3 | `BLOCKING` | M3 entry prerequisites are undefined. | Technical Lead must document the exact M3 Audio HAL SHA and M3 retest packet before M2 can be marked COMPLETE. |
| `FND-M2-003` | TTS | `NON_BLOCKING (for M2)` | Matcha legal lineage blocks final product adoption. | Legal review / disposition must be obtained before M4 final delivery. |

## 3. Reviewer Responses to Specific Questions

1. **ASR Packet Support**: Yes. The evidence supports the exact recipe for M3. Disclosing the external regression without hiding it perfectly adheres to POC guidelines.
2. **Matcha TTS Evidence**: Yes. The risk-focused evidence is sufficient for M3 technical validation. The legal limitation is correctly deferred as a blocker for final adoption/redistribution.
3. **VAD Execution Authorization**: Yes. This review formally authorizes the bounded execution of WebRTC 2.0.10 and Silero 6.2.1 against the frozen labels.
4. **VAD Profile & Gates**:
   - **WebRTC Profile**: Aggressiveness Level `3`.
   - **Padding**: `300ms` pre-speech padding, `500ms` post-speech padding.
   - **Recall & Boundary Gates**:
     - Speech-start recall `>= 95%`
     - Speech-end recall `>= 90%`
     - Start boundary error p95 `<= 300 ms`
     - End boundary error p95 `<= 700 ms`
     - Silence/noise false start `<= 1 per 10 minutes`
   - **Fallback Trigger**: Silero fallback is activated ONLY if WebRTC fails any of the above quality gates, or if it encounters a hard failure (crash, OOM, bounded timeout, incomplete cleanup). CPU, RTF, and RSS are recorded for observation only and do not trigger fallback.
5. **Required VAD Results**: A single bounded scorecard on the M1 frozen labels. It must report the exact gates above, broken down by clear/pause/silence/noise categories, plus observation of RTF, CPU, RSS, and cleanup proof. No tuning matrix is permitted.
6. **M3 Entry Scope**: Hardware topology is confirmed as Pi 5 + INMP441 + MAX98357A (VoiceHAT overlay). The exact Audio HAL SHA and the definition of the lifecycle retest packet (start/stop/cancel) must be supplied by the Technical Lead before M3 entry.

## 4. Final Recommendation

**Status**: `M2 BLOCKED`

**Next Steps**:
1. Proceed with VAD bounded execution (WebRTC first, Silero if fallback triggered) under the defined profile.
2. Submit the VAD scorecard and the proposed M3 entry locks (HAL SHA and test packet).
3. Resubmit for M2 Gate closure. M3 may not start until this gate is fully `COMPLETE`.
