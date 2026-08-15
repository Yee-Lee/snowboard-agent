# M1 Fixture and Metric Definitions v1

Status: `FROZEN`
Frozen date: 2026-08-15
Approver (Designer): User
Verifier (Tester): Test Controller

These definitions make the approved numeric gates reproducible. They apply to
all candidates in the same comparison set and may change only through change
request before real candidate results are disclosed.

## Common rules

- Use the same immutable fixture checksums, source SHA, candidate parameters,
  threads, warm-up, cold/hot definition, and repetitions.
- Use a monotonic clock for all latency boundaries.
- Report every failed item plus aggregate minimum, maximum, p50, and p95 where
  applicable. Do not replace hard failures with an average.
- A missing fixture, checksum mismatch, format mismatch, or unauthorized audio
  makes the run `INCONCLUSIVE`.

## VAD

- The label index records each utterance's speech intervals in milliseconds
  from the first PCM sample. Pause clips contain two speech intervals and one
  annotated internal-pause interval.
- A speech-start label is recalled when a candidate start occurs no earlier
  than 100 ms before and no later than 300 ms after the reference start.
- A speech-end label is recalled when a candidate end occurs no earlier than
  200 ms before and no later than 700 ms after the reference end.
- Boundary error is `candidate_ms - reference_ms`. Report signed errors and the
  p95 absolute error; the frozen start/end p95 limits remain 300/700 ms.
- More than one candidate event may not match the same reference event. Extra
  starts are false starts.
- Silence/noise false-start rate is
  `extra starts / evaluated non-speech minutes * 10`. The frozen limit is at
  most 1 per 10 minutes, and the set provides at least 10 combined minutes.
- Report clear speech, pause, silence, and noise separately before the overall
  aggregate. Endpoint/utterance policy is reported separately from frame-level
  model output when the candidate exposes both.

## ASR

- Reference language is `zh-TW`. Compute the core CER only over the
  `taiwan_mandarin` category; report code-switch, number, date, and product-term
  categories separately.
- Normalization v1 applies Unicode NFKC, lowercases Latin letters, removes
  Unicode punctuation and whitespace, and preserves Han characters, Latin
  letters, and decimal digits. It does not convert Traditional/Simplified
  Chinese or rewrite spoken numbers/dates.
- CER is Levenshtein edit distance over normalized Unicode code points divided
  by normalized reference length. Empty references are invalid.
- Sentence correctness is exact equality after normalization. Report
  `correct sentences / evaluated sentences`; do not omit empty hypotheses.
- The hard gates remain core CER <= 20% and overall sentence correctness >=
  70%. The separate categories are findings even when the aggregate passes.

## TTS

- Use the 20 tracked prompts in their fixed order and preserve each candidate's
  native PCM output without hidden Speak-layer conversion.
- The User/Designer scores intelligibility from 1 (unintelligible) to 5 (fully
  clear and correct). Record critical misread IDs separately. The hard quality
  gate is median >= 4 and no unrecorded critical misread.
- First-chunk latency starts immediately before candidate invocation and ends
  when the first non-empty PCM chunk is available. Completion ends when the
  iterator produces its terminal result and cleanup proof.
- Generation RTF is generation duration divided by rendered audio duration.
  The hard gates remain hot first-chunk p95 <= 1.5 seconds and RTF p95 <= 1.0.
