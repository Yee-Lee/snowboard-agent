# ACK-AUDIO-ASR-POST-CORRECTION-001

Status: `ACKNOWLEDGED / M4 REQUIREMENT RECORDED`

The Audio POC acknowledges
[`review_note_asr_post_correction_20260823`](../../docs/reviews/review_note_asr_post_correction_20260823.md).
The note does not alter the accepted M2 ASR primary/fallback, start a new
milestone, or authorize post-correction implementation.

The following obligation is now recorded in the M4 milestone and final delivery
checklist:

- derive systematic semantic-mishearing categories and occurrence frequencies
  from M2A/M2B evidence;
- distinguish those acoustic/semantic errors from number, date, percentage and
  other formatting differences that a downstream LLM can already understand;
- report the fixed-prompt Internal benefit and Common Voice regression;
- recommend decoder bias or context-aware post-decoder correction for Core
  evaluation; and
- keep static lexicon implementation/validation outside the Audio POC.

The final POC package will therefore deliver the raw ASR baseline, observed
semantic error patterns, and productization direction. Core owns any subsequent
implementation choice and schedule.
