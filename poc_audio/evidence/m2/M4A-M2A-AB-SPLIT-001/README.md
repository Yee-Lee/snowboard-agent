# M4A M2A A/B Split 001

Date: `2026-08-23`

Status: `SANITIZED DATA PACKET COMPLETE / PENDING INTERNAL REVIEW`

## Evidence identity

This packet recomputes the authorized A/B grouped observations from two immutable,
sanitized Pi formal reports. It performs no new inference and does not change the
frozen M2A scorecard, fixture lock, shortlist, M2B proposal, or historical evidence.

| Source | Formal row SHA-256 | POC source SHA |
| --- | --- | --- |
| small Q8 | `610bcce6949a0f5728c2f6a307bd17acf4968ccf3018f9009e235ad8da6e465a` | `629784f09f0700e7653cee4789cab8caf6d760a3` |
| base Q8 | `bb6cacc53d09c26f3bcb5d832dd374b155e3696ef5c9c6daa035d0a6cfcb81eb` | `f41a3cde6cc5d362579aae90e642356f8cbfc721` |

The common fixture lock is
`fa3649f2fde77aaaa2132cab81b6d3c562e2b812335d90e846fb6c3f85c943e6`.
The controlled manifest is
`24d3747cbcec7b5a22c7842ac92851a672dcdbe8b256e616c0abf1195dd42a9a`.

Tracked output checksums:

- `items.sanitized.json`: `b99e269880673749034866bb1601f358b1ad42784e9ecd347e54e99da42d33d1`
- `summary.json`: `8d74eec8c468a506e7829efcd5227cef4a155bd7a8e35f4c3df66d11064de50c`

## Results

| Candidate | A exact | B exact | A+B exact | A CER | B CER | A+B CER | B−A sentence gap | A−B CER improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small Q8 | 2/8 (25%) | 9/12 (75%) | 11/20 (55%) | 30/123 (24.39%) | 9/121 (7.44%) | 39/244 (15.98%) | +50.00 pp | +16.95 pp |
| base Q8 | 2/8 (25%) | 3/12 (25%) | 5/20 (25%) | 34/123 (27.64%) | 29/121 (23.97%) | 63/244 (25.82%) | 0.00 pp | +3.68 pp |

For A, both models are exact on the two Taiwan-Mandarin items and exact on none of
the six code-switch, number/date, or product-term items. For paired sentence outcomes,
A has two both-correct and six both-wrong items. B has three both-correct, six
small-only-correct, and three both-wrong items. No item is base-only correct.

The small-Q8 B advantage is material under this exact packet; base Q8 does not show a
sentence-rate A/B gap. The A category concentration supports a domain-handling
hypothesis, but no acoustic cause is claimed. A and B differ in corpus and speakers.

## Missing observations and security

Insertion/deletion/substitution components are not present in the immutable sanitized
formal rows, so they are explicitly `NOT_AVAILABLE` rather than estimated. Signal
features were not computed because this handoff did not freeze their exact definition.

The 40 tracked records contain identifiers, lengths, edit distance, correctness,
latency, RTF, RSS and hypothesis hashes. They contain no reference text, hypothesis
text, PCM, absolute controlled path, private audio or transcript.

## Reproduction

Use exact copies of the two sanitized source reports in a controlled local directory
and a new output directory:

```bash
PYTHONPATH=poc_audio/src python3 -m audio_poc.m2a_ab_split \
  --small-q8-report <small-q8-sanitized-report> \
  --base-q8-report <base-q8-sanitized-report> \
  --output-dir <new-output-dir>
```

Then compare `items.sanitized.json` and `summary.json` against the checksums above.
