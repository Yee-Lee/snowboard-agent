# M4A M2A Fixture Sensitivity Supplement 001

Date: `2026-08-22`

Status: `POST-REVIEW OBSERVATION / NO GATE EFFECT`

This compact supplement records User listening observations and a CER-only
sensitivity analysis. It does not change the frozen 20-item M2A fixture, references,
formal reports, shortlist, or M2B result.

## Listening exclusions used only for sensitivity analysis

| Item | Observation |
| --- | --- |
| A4 `asr-pause-040` | Poor recording quality and possible speaker slip. |
| A5 `asr-pause-042` | Similar but milder recording/delivery issue. |
| B1 `common_voice_zh-TW_17452147.mp3` | Not target Mandarin/Beijing pronunciation. |
| B4 `common_voice_zh-TW_19306415.mp3` | Excessive background noise. |
| B7 `common_voice_zh-TW_31328179.mp3` | Too short for meaningful sentence context. |

The filtered view contains A `6` items / `87` reference characters and B `9`
items / `102` reference characters. `CER = total edit distance / total reference
characters`; sentence exact-match rate is intentionally not repeated here.

## Aggregate CER

| Model | Frozen A | Frozen B | Frozen A+B | Filtered A | Filtered B | Filtered A+B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small Q8 | 30/123 = 24.39% | 9/121 = 7.44% | 39/244 = 15.98% | 13/87 = 14.94% | 7/102 = 6.86% | 20/189 = 10.58% |
| base Q8 | 34/123 = 27.64% | 29/121 = 23.97% | 63/244 = 25.82% | 14/87 = 16.09% | 17/102 = 16.67% | 31/189 = 16.40% |
| medium Q5 | 19/123 = 15.45% | 5/121 = 4.13% | 24/244 = 9.84% | 6/87 = 6.90% | 4/102 = 3.92% | 10/189 = 5.29% |

## Interpretation and C rule

- After fixture-quality filtering, base Q8 A/B CER converges at `16.09%` and
  `16.67%`; its combined CER improves from `25.82%` to `16.40%`. This supports
  continued bounded evaluation of base Q8, not a retrospective gate decision.
- small Q8 remains lower at filtered combined CER `10.58%`; medium Q5 is `5.29%`.
- Because exclusions were decided after formal results existed, filtered values are
  sensitivity observations only and must not replace the frozen scorecard.
- C must be human-reviewed for target indoor setting, language/accent, noise,
  meaningful duration, and spoken-reference agreement; stratify and freeze it before
  viewing candidate output.

Source reports: `survey-small-q8-629784f.sanitized.json`,
`m2b-base-q8-f41a3cd.sanitized.json`, and
`survey-medium-q5-629784f.sanitized.json` in controlled Pi storage.
