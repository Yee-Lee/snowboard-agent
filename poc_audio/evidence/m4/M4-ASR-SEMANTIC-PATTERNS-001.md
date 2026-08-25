# M4 ASR semantic-pattern and productization report

Status: `REVIEWED EVIDENCE SUMMARY / CORE FOLLOW-UP`

This report satisfies delivery checklist section 7 without adding a static
lexicon or changing the selected base-Q8 baseline. Counts below are frozen
item/category observations, not claims about population prevalence.

## Evidence-supported frequency

The base-Q8 M2A split contains eight Internal items and twelve Common Voice 26.0
zh-TW items. Internal categories contained two items each. Code-switch and
product-term categories were non-exact in 2/2 items each; general Taiwan
Mandarin was exact in 2/2. Number/date was non-exact in 2/2 but is excluded from
semantic-error frequency because spoken/written numeric formatting can preserve
meaning. Common Voice was non-exact in 9/12. Those nine items are not assigned
to semantic subtypes because the sanitized formal rows do not retain enough
transcript detail to support such a classification.

| Evidence slice | Exact | Non-exact | Interpretation |
| --- | ---: | ---: | --- |
| Internal code-switch | 0/2 | 2/2 | semantic/domain risk observed |
| Internal product terms | 0/2 | 2/2 | semantic/domain risk observed |
| Internal Taiwan Mandarin | 2/2 | 0/2 | no error in this bounded slice |
| Internal number/date | 0/2 | 2/2 | excluded from semantic-error count without human meaning review |
| Common Voice zh-TW | 3/12 | 9/12 | non-exact frequency only; subtype unavailable |
| Full base-Q8 A+B | 5/20 | 15/20 | raw exact/CER observation, not semantic-error frequency |

Observed semantic-shift exemplars from the reviewed raw-error note include
near-homophone `測試` becoming `確實`, tone/question shift `哪個` becoming `那個`,
and a domain compound such as `是硬（體）` becoming the generic word `適應`.
These exemplify three patterns—near-homophone substitution, tone-driven intent
change and domain-term decomposition—but the sanitized packet cannot support an
honest exact per-pattern occurrence count. No count is invented.

## Prompt-bias result and limitation

On the 8 Internal + 4 Common Voice development slice, the same fixed 109-byte
domain prompt changed base-Q8 Internal raw CER from 17.708333% to 5.208333% and
sentence correctness from 37.5% to 75.0%. It recovered all five expected domain
terms with no unexpected insertion. Common Voice raw CER improved, but reviewed
task-adjusted scoring regressed by one edit (`1` to `2`) because a new
`館`→`管` substitution appeared. Small-Q8 showed the same Common Voice +1 adjusted
edit regression. Therefore fixed prompting is useful bias, not universal
correction, and the raw baseline remains preserved.

Pure display normalization—spoken versus written numbers, dates, temperatures
or percentages—is not treated as acoustic recognition failure when downstream
reasoning preserves meaning. Conversely, a semantic shift cannot reliably be
reconstructed by an LLM after the acoustic evidence has been discarded.

## Core productization recommendation

Keep correction after the decoder or within decoder biasing; do not place it in
the Audio HAL or mutate the POC wrapper contract. Core should evaluate N-best
domain rescoring, stronger hotword/keyword bias, or context-aware post-decoder
correction using product intent/state. A hand-written static replacement lexicon
is not recommended because it is model-specific, incomplete and vulnerable to
false corrections. Personalization is a separate product-layer decision.

Sources: `M4A-M2A-AB-SPLIT-001/summary.json`, the base/small Q8 prompt-dev
reports, and `docs/reviews/review_note_asr_post_correction_20260823.md`.
