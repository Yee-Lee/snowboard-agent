# CR-AUDIO-M2-VAD-METHOD-CORRECTION-001

Status: `DRAFT / USER METHOD APPROVED / REVIEWER CONFIRMATION REQUIRED`

## Trigger

The published M2 VAD scorecard cannot support candidate rejection or no-go.
Post-run inspection found three method defects:

1. The WebRTC engine state persisted across independent WAV fixtures while the
   external endpoint state reset at every file boundary. The run was therefore
   neither an independent-fixture test nor a continuous-stream test.
2. The Silero adapter omitted the official 64-sample context prepended to every
   512-sample 16 kHz model window. A four-fixture sanity check restored speech
   probabilities from below `0.004` to above `0.997` without changing the model
   or threshold.
3. The scorer treated every annotated pause interval as a separate utterance
   endpoint and scored unpadded model boundaries. The User confirms that the
   labels intentionally include manual boundary buffer and that preserving one
   event across a natural pause is valid product behavior.

The User also confirmed that each fixture contains a device-start transient of
approximately 140 ms. This transient is not speech. Frame-aligned evaluation
must ignore the first 160 ms after device open or fixture start, while retaining
later impact noise as real false-positive risk.

## Corrected method approved by the User

- Input remains 16 kHz mono S16_LE with exact candidate-native frames/windows.
- Reset engine and endpoint state together for every independent fixture.
- Ignore the first 160 ms after fixture/device start; do not feed those frames
  into candidate state.
- WebRTC remains aggressiveness level 3.
- WebRTC onset requires at least 14 voiced frames in a complete rolling 15-frame
  window: 90% of 300 ms at 20 ms per frame.
- Keep the existing 500 ms consecutive-nonspeech endpoint close condition.
- Preserve 500 ms before detected start and 600 ms after detected end for the
  capture interval supplied downstream.
- Treat each clear or pause WAV as one utterance. For pause fixtures, the
  reference envelope runs from the first annotated speech start to the final
  annotated speech end. One event across the internal pause is valid.
- Merge overlapping or touching padded capture intervals only for utterance
  coverage analysis. Count distinct non-speech endpoint activations separately.
- Score start and end recall by whether the padded capture retains the reference
  utterance start and end. Report raw model boundaries and errors as diagnostic
  observations rather than using manually buffered labels to reject a row.
- Preserve the silence/noise false-start gate at no more than one activation per
  ten evaluated minutes. Confirmed later impact/knock noise remains in scope.
- Silero must implement the pinned 6.2.1 official recurrent-state and 64-sample
  context contract before any fallback result is eligible for scoring.
- No mode, threshold, debounce, padding, or candidate matrix is authorized.

## Gate impact

This correction changes the interpretation of frozen endpoint and boundary
evidence after an invalid run. It does not retrospectively turn the old result
into a pass. The old WebRTC and Silero JSON files remain immutable rejected test
evidence, but their `FAIL` and no-go disposition is withdrawn pending a single
corrected bounded run.

Reviewer confirmation is required before the corrected run becomes formal M2
evidence. Until then, VAD is `INCONCLUSIVE / METHOD CORRECTION PENDING`, M2
remains blocked, and M3 must not start.

## Proposed bounded recovery

1. Implement the corrected adapters and focused deterministic unit tests.
2. Run one clear, one pause, one silence, and one confirmed knock/noise fixture
   as a non-scoring sanity packet.
3. Present the sanity output and exact rerun packet to the User.
4. After User publication confirmation and Reviewer method confirmation, run
   one 100-fixture Pi pass for WebRTC.
5. Run corrected Silero only if the authorized WebRTC fallback trigger fires.

No result report, milestone disposition, candidate advance/reject, or no-go may
be committed, pushed, or submitted before explicit User confirmation.
