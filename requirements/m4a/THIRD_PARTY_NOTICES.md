# M4a third-party notices and redistribution inventory

This file covers every direct runtime, model, native source and unpacked
component in the checksum-locked M4a Audio product. Artifact identities and
immutable source locators are in `audio-artifacts.json`; extracted Matcha file
identities are in `matcha-closure.json`. The product installer preserves wheel
license metadata and installs this notice file with the product.

The selected third-party artifacts are unmodified. Core's native wrapper and
Python adapters are separate integration code. If a distributor modifies a
third-party artifact, it must add the modification notices required by that
artifact's license. A product release must ship the complete upstream license
texts named below; this inventory is not a substitute for those texts.

## Silero VAD

| Included component | Version / identity | License and required notice |
| :--- | :--- | :--- |
| Silero VAD model and project | 6.2.1 / commit `7e30209a3e901f9842f81b225f3e93d8199902b1` | MIT; retain the upstream Silero copyright and MIT text. |
| ONNX Runtime | 1.29.0 | MIT; retain the wheel's `dist-info` license files and Microsoft attribution. |
| NumPy | 2.5.2 | BSD-3-Clause; retain NumPy's copyright, BSD text and notices for libraries bundled in the wheel. |
| FlatBuffers | 25.12.19 | Apache-2.0; retain the Apache-2.0 text and upstream notices. |
| Packaging | 26.3 | Apache-2.0 OR BSD-2-Clause; retain both texts supplied by the wheel. |
| Protobuf | 7.36.0 | BSD-3-Clause; retain the upstream copyright and BSD text supplied by the wheel. |

The VAD runtime is installed from only these five wheels. No optional provider,
downloader or system-site package is part of the product closure.

## whisper.cpp

whisper.cpp 1.9.2, pinned source commit
`306c88f4d1286aec1bf96e544632897886af5501`, is MIT-licensed. Preserve its
exact upstream `LICENSE`. The product uses a CPU-only build and excludes the
optional media-codec, server, network and accelerator components, so their
licenses are not part of this binary closure.

## Whisper model

The `ggml-base-q8_0.bin` artifact is pinned to the ggerganov whisper.cpp model
repository revision `5359861c739e955e79d9a303bcbc70fb988958b1`. The model
repository, whisper.cpp and upstream OpenAI Whisper materials declare MIT;
preserve the copyright and MIT notices from all three upstream projects with
the model distribution.

## sherpa-onnx runtime

| Included component | Version | License and required notice |
| :--- | :--- | :--- |
| sherpa-onnx wrapper wheel | 1.13.5 | Apache-2.0; retain upstream `LICENSE`, any `NOTICE`, and wheel metadata. |
| sherpa-onnx-core native wheel | 1.13.5 | Apache-2.0; retain upstream `LICENSE`, any `NOTICE`, and bundled native-component notices from the wheel. |
| NumPy | 2.5.2 | BSD-3-Clause; same NumPy and bundled-library obligations listed under Silero VAD. |

The exact source baseline is sherpa-onnx commit
`3dc7c569f31ca2cd4a20ed6f7db780327e6714c5`. The acoustic model and vocoder
below have separate notices and are not covered merely by the runtime license.

## Matcha acoustic model

The acoustic archive and `model-steps-3.onnx` are bound to the author repository
`dengcunqin/matcha_tts_zh_en_20251010` at commit
`f05803ec98df733d5775dfb0c40a919ae699cfb6`. Its pinned model card declares
Apache-2.0 and identifies model author `dengcunqin`; preserve that attribution,
the pinned model card and the Apache-2.0 text. The archive itself contains no
LICENSE or NOTICE, so the external notice bundle is mandatory.

The archive's 362-file extracted closure includes these component classes:

| Embedded component | Product paths / identity | Redistribution treatment |
| :--- | :--- | :--- |
| Acoustic weights and metadata | `model-steps-3.onnx`, `README.md` | Pinned author-model Apache-2.0 declaration and attribution above. |
| Token and pronunciation data | `tokens.txt`, `lexicon.txt` | Distributed as part of the pinned author model; preserve author-model Apache-2.0 declaration and attribution. |
| Chinese normalization FSTs | `date-zh.fst`, `number-zh.fst`, `phone-zh.fst` | Distributed as part of the pinned author model; preserve author-model Apache-2.0 declaration and attribution. |
| eSpeak NG compiled data | `espeak-ng-data/**` | Conservatively retain eSpeak NG GPL-3.0-or-later, Apache-2.0, BSD-2-Clause and Unicode data notices, and satisfy corresponding-source obligations applicable to the distributed data. |

Matcha-TTS architecture source is MIT-licensed; retain its MIT attribution when
architecture materials are distributed. No archive file is changed by Core.

Accepted risk: the unnamed mixed Chinese/English training-data and voice lineage
remains USER-owned. This decision does not waive any license,
attribution, corresponding-source or notice obligation and must remain visible
before shipment.

## Vocos

The exact `vocos-16khz-univ.onnx` is bound to the same pinned ModelScope commit
and author, which declares Apache-2.0 for the repository. Preserve the pinned
model-card attribution and Apache-2.0 text. The Vocos architecture project is
MIT-licensed; preserve its upstream MIT notice if architecture source or
derived implementation material is distributed. The release asset itself has
no embedded notice, so this external entry is mandatory.

## Required release texts

A redistributable package must include, at minimum, the exact upstream texts
for Apache-2.0, MIT, BSD-3-Clause, BSD-2-Clause, GPL-3.0-or-later and the
Unicode data license, plus every license/notice file embedded in the installed wheels.
The pinned Matcha model card and archive README must also be retained as model
attribution. Removal of wheel metadata or any of these notices is not allowed
by the M4a packaging profile.
