# RESP-AUDIO-M2A-AB-SPLIT-001

Date: `2026-08-23`

Status: `READY FOR INTERNAL INTAKE / GROUPED OBSERVATIONS ONLY`

## Delivery identity

- Branch: `audio`
- Data-packet candidate SHA: `63ce6e3ff736f9a0a02c8745b5f424fba8c6c38d`
- Input handoff: `docs/pm_handoff/Audio_POC_AB_experiement.md`
- Evidence: `poc_audio/evidence/m2/M4A-M2A-AB-SPLIT-001/`
- `items.sanitized.json` SHA-256:
  `b99e269880673749034866bb1601f358b1ad42784e9ecd347e54e99da42d33d1`
- `summary.json` SHA-256:
  `8d74eec8c468a506e7829efcd5227cef4a155bd7a8e35f4c3df66d11064de50c`

The packet contains 40 sanitized records: exact 20-item rows for small Q8 and
base Q8. Source report checksums are pinned and matched the reviewed Pi evidence.
No inference was rerun. The frozen M2A scorecard, references, shortlist and M2B
proposal are unchanged.

## Grouped observations

| Candidate | A exact / CER | B exact / CER | A+B exact / CER | Sentence gap B−A | CER improvement A−B |
| --- | ---: | ---: | ---: | ---: | ---: |
| small Q8 | 2/8, 24.39% | 9/12, 7.44% | 11/20, 15.98% | +50.00 pp | +16.95 pp |
| base Q8 | 2/8, 27.64% | 3/12, 23.97% | 5/20, 25.82% | 0.00 pp | +3.68 pp |

Both candidates are exact on the two A Taiwan-Mandarin items and exact on none
of the six A code-switch, number/date or product-term items. Paired A outcomes
are two both-correct and six both-wrong. Paired B outcomes are three
both-correct, six small-only-correct and three both-wrong; none are base-only.

The small-Q8 B advantage is material in this exact packet, while base Q8 has no
A/B sentence-rate gap. The category pattern supports a domain-handling
hypothesis. It does not establish an acoustic or recording-quality cause because
A and B differ in corpus and speakers and no signal-feature causal analysis ran.

## Missing fields and security

Insertion/deletion/substitution components were not present in the immutable
sanitized source rows and are marked unavailable. Signal features were not
computed because no exact definition was frozen for this handoff. No values were
estimated.

The committed packet contains no reference text, hypothesis text, PCM, absolute
controlled path, private audio or transcript. It includes only identities,
lengths, edit distance, correctness, latency, RTF, RSS and hypothesis hashes.

## Reproduction and validation

The exact command is recorded in the evidence README and `summary.json`, using
controlled copies of the two sanitized source reports. Validation completed:

- deterministic regeneration produced byte-identical JSON;
- source SHA-256, candidate/artifact identity, fixture lock, 8:12 grouping,
  cleanup and security boundaries were enforced;
- `PYTHONPATH=poc_audio/src python3 -m unittest discover -s poc_audio/tests -v`
  passed all 140 tests.

## Disposition

This response completes the requested data packet and is ready for Designer/PM
intake. It does not declare a winner, change a gate, or authorize further ASR
inference. M2 remains `AT_RISK` pending ASR comparative selection review, Matcha
remaining gates and an authorized VAD finalist/no-go path.
