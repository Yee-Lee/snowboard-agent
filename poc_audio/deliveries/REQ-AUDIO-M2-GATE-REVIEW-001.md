# REQ-AUDIO-M2-GATE-REVIEW-001

Status: `READY FOR REVIEW`

## Request

Audio POC requests a formal M2 Gate pre-review covering ASR, TTS, VAD, and M3
entry readiness. This is not a request to mark M2 `COMPLETE` before the open
findings are resolved. The requested output is a bounded list of accepted
dispositions, blocking findings, required evidence, and the exact work needed
to reconvene and close the M2 gate.

Evidence baseline: `audio` commit
`36df2ef1c98ac14ff55940f5a2809b84e080c1bc`.

## Current proposed dispositions

| Track | Proposed M2 disposition | Evidence / remaining boundary |
| --- | --- | --- |
| ASR | base Q8 primary; small Q8 fallback; both use P0 + greedy + fixed domain prompt | Review the bounded C-v1 raw/adjusted scorecard, exact recipe, and disclosed Common Voice `+1 edit` regression. No further ASR inference matrix is proposed. |
| TTS | Matcha 1.13.5 advances as M3 finalist | Risk-focused lifecycle, true network-disabled P12, material resource/thermal risk, and ten-prompt User quality passed. Legal lineage remains blocking for redistribution, product adoption, and final-winner approval, but not for internal M3 technical validation. |
| VAD | WebRTC 2.0.10 primary; Silero 6.2.1 conditional fallback | User has ACKed this strategy. M2 still needs reviewer confirmation of the execution authorization boundary, exact WebRTC aggressiveness/shared endpoint profile, aggregate frozen-label recall gate, and evidence required for finalist/no-go. VAD execution and selection are part of M2, not post-gate work. |
| M3 entry | `NOT_READY` pending M2 closure | Review must identify the exact pinned Audio HAL SHA, target hardware scope, finalist artifacts, and M3 retest packet required before entry. |

## Evidence set for review

- M2 status and exit gate:
  [`docs/milestone/m2_candidate_evaluation.md`](../../docs/milestone/m2_candidate_evaluation.md)
- ASR proposed recipe and bounded scorecard:
  [`M2B-C-ASR-RECIPE-PROPOSAL-001`](../evidence/m2/M2B-C-ASR-RECIPE-PROPOSAL-001.md) and
  [`M2B-C-PUBLIC-SCORECARD-001`](../evidence/m2/M2B-C-PUBLIC-SCORECARD-001.md)
- TTS risk-focused decision:
  [`M4A-G1B-WP3-MATCHA-RISK-REVIEW-001`](../evidence/m2/M4A-G1B-WP3-MATCHA-RISK-REVIEW-001.md)
- VAD scope request and recorded User strategy:
  [`CR-AUDIO-M4A-G1B-VAD-SCOPE-001`](CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md) and
  [`RESP-AUDIO-M4A-G1B-VAD-SCOPE-001`](RESP-AUDIO-M4A-G1B-VAD-SCOPE-001.md)
- Current consolidated reviewer status:
  [`docs/reviews/reviewer_report_M2_20260823.md`](../../docs/reviews/reviewer_report_M2_20260823.md)
- M3 entry scope:
  [`docs/milestone/m3_real_hardware_integration.md`](../../docs/milestone/m3_real_hardware_integration.md)

## Questions requiring reviewer disposition

1. Does the ASR packet support the proposed base Q8 primary, small Q8 fallback,
   and exact recipe for M3, with the disclosed external regression retained as
   a trade-off rather than hidden?
2. Is the Matcha risk-focused evidence sufficient for M3 finalist disposition,
   with its legal limitation correctly deferred only for internal technical
   validation and still blocking final adoption/redistribution?
3. Does the recorded User ACK authorize the exact VAD candidate rows for M2
   execution? If not, identify the missing decision owner or wording precisely.
4. What exact WebRTC aggressiveness, endpoint/padding profile, aggregate
   start/end recall gate, and fallback trigger must be frozen before execution?
5. Which VAD results are required to declare WebRTC finalist, activate the
   Silero fallback, or issue evidence-backed no-go without expanding into a
   tuning matrix?
6. What exact M3 Audio HAL SHA, hardware topology, candidate identities, and
   retest packet must be fixed before M3 can start?

## Requested response

Please return one response at
`docs/reviews/RESP-AUDIO-M2-GATE-REVIEW-001.md` with:

- disposition for each of ASR, TTS, VAD, and M3 entry;
- findings classified as `BLOCKING`, `NON_BLOCKING`, or `ACCEPTED`;
- exact evidence or decision needed to close every blocking finding;
- confirmation that VAD evaluation remains inside M2;
- final recommendation of `M2 COMPLETE`, `M2 CONDITIONAL`, or `M2 BLOCKED`.

Until that response and its required findings are closed, the milestone remains
`M2 IN_PROGRESS`, final delivery reachability remains `AT_RISK`, and M3 remains
`NOT_STARTED`.
