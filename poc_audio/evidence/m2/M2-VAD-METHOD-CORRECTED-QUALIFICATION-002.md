# M2 VAD method-corrected qualification

Status: `USER REVIEWED / SILERO CONDITIONAL FINALIST PROPOSED / REVIEWER CLOSURE PENDING`

## Executive disposition

The original WebRTC/Silero no-go is withdrawn because its method did not
represent the required product behavior and the Silero adapter omitted the
official model context. The immutable old SHAs and JSON files remain rejected
method evidence; they do not reject either engine.

One corrected WebRTC profile and one corrected Silero profile were subsequently
run on the same 100 Pi fixtures. WebRTC's fixed 300 ms / 90% onset debounce
reduced impact-noise activations but caused severe normal-speech recall loss and
does not advance. Silero 6.2.1 is proposed as the M3 provisional VAD finalist
with a named low-volume speech-start blocker for target-mic qualification.

Silero is not relabelled `PASS` against the frozen 95% start-recall gate. This
is an evidence-backed conditional-advance request, not retrospective gate
relaxation.

## Method correction

The User confirmed the required evaluation semantics before the corrected
full runs:

- mask the first frame-aligned 160 ms after device/fixture start because the
  recordings contain a confirmed device-start transient;
- reset engine and endpoint state together for every independent WAV;
- preserve 500 ms before detected start and 600 ms after detected end;
- evaluate each pause WAV as one utterance envelope from first annotated start
  to final annotated end; preserving one event across the pause is valid;
- use padded capture retention for start/end scoring and retain raw model
  boundary error only as a diagnostic because the labels intentionally contain
  manual buffer;
- keep later impact/knock noise as genuine non-speech risk; and
- publish no candidate score or disposition before explicit User review.

The correction rationale is fixed in
[`CR-AUDIO-M2-VAD-METHOD-CORRECTION-001`](../../deliveries/CR-AUDIO-M2-VAD-METHOD-CORRECTION-001.md).

## Immutable execution binding

| Row | Exact Pi SHA | Controlled draft result | Result SHA-256 |
| --- | --- | --- | --- |
| WebRTC 2.0.10 corrected endpoint | `d342fea7cb5ea52050d13f5f0b088aad297df87a` | `~/.local/share/audio-poc/m2/vad-webrtc-d342fea-draft-001.json` | `011938a7f3853cff217c619511cca72b6ec6d21281491699f35ea335d6adf600` |
| Silero 6.2.1 official-context profile | `5188e3af360ba3b63f5eedb16288d39bc849cacc` | `~/.local/share/audio-poc/m2/vad-silero-5188e3a-draft-001.json` | `93ca6d3d91842922240a84450145fc949bee69850d0003e37608f705fb0225a4` |

Both runs used the immutable 25 clear, 25 pause, 25 silence and 25 noise WAV
fixtures and the same reviewed label index. No model, private audio or raw
transcript is committed.

## Corrected WebRTC observation

WebRTC retained aggressiveness level 3 and used a complete rolling 300 ms
window requiring 14/15 voiced frames before onset. It used the corrected state,
startup, padding and utterance semantics.

| Observation | Corrected WebRTC |
| --- | ---: |
| Start retention | `27/50` (`54%`) |
| End retention | `39/50` (`78%`) |
| Complete utterance coverage | `20/50` (`40%`) |
| Silence activations | `0` |
| Recorded noise activations | `2` in one fixture |
| Cleanup / throttle | `PASS` / none |

The two recorded noise events were in `vad-noise-006`. User listening found a
cough and computer speech rather than pure environmental noise. They remain
vocal-interference/playback-speech observations, not evidence that a basic VAD
can identify source or intent. The fixed debounce rejected known knock noise
but was too aggressive for normal Taiwan Mandarin. No onset tuning matrix was
run; this exact WebRTC profile does not advance.

## Corrected Silero profile and result

Silero used exact model SHA-256
`1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`,
official recurrent state and 64-sample context, 512-sample windows, threshold
`0.5`, exit hysteresis below `0.35`, minimum speech duration 250 ms, 500 ms
silence close, and product 500/600 ms capture padding. It did not inherit the
failed WebRTC voiced-ratio debounce.

| Observation / gate | Corrected Silero | Disposition |
| --- | ---: | --- |
| Start retention | `39/50` (`78%`) | Numeric frozen gate not met |
| End retention | `49/50` (`98%`) | Meets 90% gate |
| Complete utterance coverage | `38/50` (`76%`) | Observation |
| Silence activations | `0` | Clean |
| Silence/noise activation rate | `1/10 min` | Meets gate exactly |
| Raw start/end boundary p95 | `954/290 ms` | Diagnostic only under corrected label semantics |
| Wall / RTF | `7.027739 s / 0.00739762` | Observation |
| Peak RSS | `80.390625 MiB` | Observation |
| Cleanup | zero delta / no audio owner | Pass |
| Temperature / throttle | `36.4 -> 38.6 C / 0x0 -> 0x0` | Bounded |

The only non-speech activation was `vad-noise-008`, raw `192–928 ms`, padded
`0–1528 ms`. User replay of the exact crop confirmed two object impacts and no
sigh or speech. The two impacts formed one endpoint activation, so the frozen
rate is exactly one activation per ten minutes.

## User risk-focused capture review

Because the human labels intentionally include manual buffer, the User reviewed
the exact downstream capture—not only the full WAV—for all numeric start misses
with more than 300 ms shortfall, plus the sole no-event speech fixture and sole
non-speech activation.

| Fixture | Exact capture review | Disposition |
| --- | --- | --- |
| `asr-clear-010` | Capture began near the second syllable of `喇叭`; first `喇` absent | Confirmed leading-syllable loss |
| `asr-clear-014` | `請記錄` remained audible but quiet | Numeric miss caused by label buffer; practical capture retained |
| `asr-clear-022` | Capture began around `五`; `星期` absent | Confirmed leading-word loss |
| `asr-pause-034` | Initial `請` was not reliably present | Confirmed leading-syllable loss |
| `asr-pause-047` | Capture began around `天`; initial `今` absent | Confirmed leading-syllable loss |
| `asr-pause-037` | No Silero event; full WAV was low volume with mechanical sound at start/end | Confirmed hard low-volume fixture failure |
| `vad-noise-008` | Two object impacts; no sigh/speech | One genuine impact-noise activation |

Five additional numeric start misses with at most 190 ms shortfall were not
individually replayed because the confirmed failures already prevent a 95%
start-retention claim and further listening would not change the M2 risk
decision. They remain disclosed rather than silently reclassified.

## Recommendation and deferred work

Silero materially outperforms the corrected WebRTC endpoint on normal speech,
end retention and environmental-noise rejection. Its remaining failures are
concentrated in low-volume leading syllables. Adjusting fixture-specific gain,
threshold or padding in M2 would create the tuning matrix that the User
explicitly declined and could overfit recordings whose level, device transient
and mechanics differ from the final target microphone.

The Technical Lead therefore recommends:

1. advance Silero 6.2.1 as the M3 provisional VAD finalist under this exact
   model/runtime profile;
2. retain start retention as a blocking M3 target-mic qualification risk rather
   than claiming M2 quality `PASS`;
3. determine any fixed front-end gain only on the pinned M3 mic/HAL, with
   clipping and silence/impact-noise regression checks and no threshold matrix;
4. keep computer playback and cough as source/intent observations; basic VAD
   alone is not expected to perform AEC or speaker-source rejection; and
5. do not tune or rerun either M2 VAD row after this reviewed disposition.

Reviewer/Designer acceptance of this conditional advance and the corrected M3
entry lock is required before M2 becomes `COMPLETE`.
