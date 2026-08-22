# M2B C reference erratum

Date: 2026-08-22  
Status: `APPLIED / COMPLETE 24-ITEM LABEL AUDIT REVIEWED`

User audio review identified a transcription mismatch in one frozen Internal
holdout reference. Existing inference and scoring artifacts remain immutable;
only the existing hypotheses were rescored against the corrected controlled
reference. No audio, transcript, hypothesis, or User comment is committed.

| Candidate/profile | Raw edits old → corrected | Adjusted edits old → corrected | Correct sentence |
| --- | ---: | ---: | ---: |
| Base baseline | 3 → 1 | 3 → 1 | no change |
| Base prompt | 3 → 1 | 3 → 1 | no change |
| Small baseline | 2 → 0 | 2 → 0 | incorrect → correct |
| Small prompt | 4 → 2 | 4 → 2 | no change |

The audio identity, old/corrected reference hashes, controlled erratum hash,
row deltas, and corrected aggregates are frozen in
[`m2b_c_reference_erratum.json`](../../manifests/m2b_c_reference_erratum.json).
This correction does not authorize general label changes after observing model
output. Blind-first review subsequently confirmed the remaining 23 references;
the bounded scorecard may now be cited with its stated scope and limitations.
