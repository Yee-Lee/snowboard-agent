# M4 Matcha license and lineage audit correction

Status: `MODEL LICENSE FOUND / DATA LINEAGE AND NOTICE CLOSURE PENDING`

Date: 2026-08-25

This append-only audit corrects the overly broad statement that the selected
Matcha model lacked an explicit license. It does not alter any technical result,
artifact identity or frozen gate.

## Exact model-license evidence

The selected acoustic model is bound to ModelScope repository
`dengcunqin/matcha_tts_zh_en_20251010` at commit
`f05803ec98df733d5775dfb0c40a919ae699cfb6`. Its pinned `README.md` front matter
explicitly declares `license: Apache License 2.0`. The pinned repository file
API identifies `model-steps-3.onnx` as SHA-256
`524286bf6cf11be74329ae1c682ac69e34d6860c2ea9fd1290319d561540b16a`; this is
the same acoustic model extracted from the POC archive. The exact repository
also identifies `vocos-16khz-univ.onnx` as SHA-256
`b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e`.

Authoritative locators:

- `https://modelscope.cn/models/dengcunqin/matcha_tts_zh_en_20251010/resolve/f05803ec98df733d5775dfb0c40a919ae699cfb6/README.md`
- `https://modelscope.cn/api/v1/models/dengcunqin/matcha_tts_zh_en_20251010/repo/files?Revision=f05803ec98df733d5775dfb0c40a919ae699cfb6`
- `https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/matcha-icefall-zh-en.html`

Therefore the model license is not `UNKNOWN`: the publisher/author assigned
Apache-2.0 to the pinned model repository. The sherpa-onnx runtime remains
Apache-2.0 independently. Matcha-TTS architecture source is MIT, which does not
replace or conflict with the model-specific Apache-2.0 declaration.

## Remaining closure gap

The same pinned model card says only that this voice was fine-tuned from
`dengcunqin/matcha_tts_zh_en`. The base card says it was trained from mixed
Chinese/English data, but names no dataset, source owner, consent/voice rights,
or commercial and redistribution terms. The archive and pinned ModelScope file
lists contain no embedded `LICENSE` or `NOTICE`; accompanying lexicon, FST,
tokens and `espeak-ng-data` therefore still need a component provenance/notice
inventory for redistribution packaging.

This yields the corrected disposition:

| Question | Evidence-backed answer |
| --- | --- |
| Is an explicit model license published? | Yes — Apache-2.0 at the pinned author repository |
| Is the tested model identity bound to it? | Yes — exact ONNX SHA matches the archive |
| Is the full training-data lineage public? | No — only “mixed Chinese/English data” is stated |
| Is a complete redistribution notice bundle present? | No — archive/repository has no embedded LICENSE/NOTICE and component notices are incomplete |
| May Audio POC issue a legal clearance? | No — Core/User legal disposition remains required |

## Required resolution

Core should no longer report “no Matcha model license.” It should either accept
the pinned Apache-2.0 grant with a completed Apache/component notice bundle and
document its training-data risk decision, or request from the model author:

1. the exact Chinese and English training datasets and their terms;
2. confirmation of the right to license the resulting weights for commercial
   use, modification and redistribution;
3. the required copyright, attribution and third-party notices for the model,
   Vocos, lexicon/FST/tokens and espeak data.

The author model card publishes a contact email and WeChat handle. Audio POC has
not contacted the author because external communication requires separate User
authorization. If closure cannot be obtained, the existing conditional product
no-go remains reversible: Matcha retains internal technical evidence, and Core
must select a TTS with complete licensing and data lineage for product use.
