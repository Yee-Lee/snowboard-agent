# RESP-AUDIO-M4-GATE2B-001

- **Date**: 2026-08-25
- **From**: Core Designer
- **To**: Audio POC Team
- **References**: `DELIVERY-AUDIO-M4-GATE2B-001`, `ADDENDUM-AUDIO-M4-MATCHA-LICENSE-001`
- **Delivery ID**: `POC-audio-DEL-2026-001-R1`
- **Status**: `ACCEPTED — AUDIO M4 MAY CLOSE; ALL THREE FINAL REFERENCES APPROVED`
- **Core response path**: `docs/outsource/responses/RESP-AUDIO-M4-GATE2B-001.md`
- **Core branch**: `core`
- **Core response commit**: supplied after the USER-approved commit; this file does not self-reference its future commit

## 1. Exact intake

Core acknowledges the following immutable identities:

| Identity | Accepted value |
| :--- | :--- |
| Original Audio delivery branch / SHA | `audio` / `b0159b5ae7862d47f1c860ebaaa7108cc0a9876f` |
| Corrected Audio delivery branch / SHA | `audio` / `ca51bce9b4e205d9c9faf004d41c27169f108a3f` |
| P9.1 and combined execution SHA | `8be3bc095b504b8eab1dfeb21b94173728b9656f` |
| Failure/recovery execution SHA | `26f33a3c371eee61df46924432839d0fa9ee3bf8` |
| Core HAL execution SHA | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| P9.1 controlled evidence SHA-256 | `5883a6399c6d183d18bb7fb7a98fc7a60b6b42396fd5bde46168ae625e3ac880` |
| Combined controlled evidence SHA-256 | `c48adb395eae6db5ae69c544be6ef1228ad331cd08091507c5186846199c4810` |
| Failure/recovery controlled evidence SHA-256 | `68d4f77b6f8a372f15c590c0fb4065154fa6c21c18aa1d2cf4a00b034a711862` |

The Audio worktree was clean and `audio` resolved exactly to corrected delivery
SHA `ca51bce9b4e205d9c9faf004d41c27169f108a3f` during final review. The append-only
correction changes Matcha license wording only; the execution identities,
controlled evidence hashes and portable-kit hashes remain unchanged.

## 2. Gate 2B and portable-kit review

### Findings

**Blocking findings: none.**

| Review area | Result | Evidence |
| :--- | :--- | :--- |
| P9.1 realistic residency | **PASS** | 20/20; peak `3339.688 MiB` within `3584 MiB`; zero swap; no throttling; cleanup zero |
| Independent combined execution | **PASS** | 20/20; every VAD/ASR/TTS stage `SUCCESS`; network namespace offline; cleanup zero |
| Failure/recovery | **PASS** | 12/12 expected terminals and 12/12 same-finalist recoveries; all tracked cleanup categories zero |
| Portable packet and schemas | **PASS** | packet, packet schema, result schema and runner SHA-256 values match the delivery manifest |
| Local validation | **PASS** | `bash poc_audio/tools/run_m4_combined.sh validate` returned 20 sessions and 12 failure cases |
| Portable regression | **PASS** | `PYTHONPATH=poc_audio/src python3 -m pytest -q -p no:cacheprovider poc_audio/tests` returned `214 passed` |
| Data-safety boundary | **PASS** | submitted commit contains no model, audio, wheel, native binary, secret or raw-result payload |

**Advisory `ADV-AUDIO-M4-001`**: keep `PYTHONPATH=poc_audio/src` explicit in the
source-tree regression command. Without that environment, the force-abort child
cannot import `audio_poc`; this is a test-launch setup issue, not a finalist or
formal evidence failure, and does not block acceptance.

Controlled raw evidence remains outside Git by design. Core accepts the three
immutable controlled locators and hashes together with the sanitized reviewed
reports; this response does not claim that Core Git contains or independently
redistributes those raw artifacts.

## 3. Finalist license disposition

This is Core's engineering intake and packaging disposition, not a substitute
for legal counsel or a warranty of third-party rights.

### Silero VAD 6.2.1 ONNX — accepted

The exact Silero repository and source-embedded ONNX are covered by the upstream
MIT license. Internal evaluation, Gate 2B final-reference use, product
integration and redistribution are approved, provided the complete Silero MIT
copyright and permission notice accompanies distributions.

Reference: [Silero VAD upstream LICENSE](https://github.com/snakers4/silero-vad/blob/7e30209a3e901f9842f81b225f3e93d8199902b1/LICENSE).

### whisper.cpp 1.9.2 base Q8 — accepted

The exact whisper.cpp source is MIT, the pinned `ggerganov/whisper.cpp` model
repository declares MIT, and OpenAI Whisper publishes both code and model
weights under MIT. Internal evaluation, Gate 2B final-reference use, product
integration and redistribution of this exact CPU-only engine/model combination
are approved, provided the whisper.cpp, model-repository and OpenAI Whisper MIT
notices are retained. This approval does not include optional GPL or unrelated
media-codec components.

References: [whisper.cpp LICENSE](https://github.com/ggml-org/whisper.cpp/blob/306c88f4d1286aec1bf96e544632897886af5501/LICENSE), [pinned base-Q8 model repository](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1), [OpenAI Whisper](https://github.com/openai/whisper).

### Matcha zh/en + Vocos 16 kHz — accepted with USER-owned lineage risk

The `sherpa-onnx==1.13.5` runtime is Apache-2.0. The pinned author ModelScope
repository at `f05803ec98df733d5775dfb0c40a919ae699cfb6` explicitly declares
`Apache License 2.0`; its `model-steps-3.onnx` and Vocos SHA-256 identities match
the tested artifacts. Core therefore acknowledges an explicit Apache-2.0 model
grant and does not classify the Matcha weights as unlicensed.

The archive still lacks embedded `LICENSE` / `NOTICE` copies, a complete
component-notice inventory and named mixed Chinese/English training datasets.
The USER explicitly directs Core to treat the Matcha license as usable and
accepts the remaining product-licensing and training-data-lineage risk. Core
records that gap as **Accepted Risk**, not a Gate 2B blocker.

The resulting boundary is:

| Use | Disposition |
| :--- | :--- |
| Internal isolated/offline POC evaluation | **Approved** |
| Audio M4 final reference | **Approved** |
| Core product integration / dependency lock | **Approved** for the exact checksum-pinned runtime, model and Vocos identities |
| Model, vocoder, archive or bundled-product redistribution | **Approved with packaging obligations**: retain Apache-2.0 text, attribution, modification notices where applicable, and complete the third-party component notice inventory before shipment |
| Product use or redistribution of generated voice output | **Approved by USER risk decision**, subject to the project's normal content and product policies |

References: [pinned author ModelScope card](https://modelscope.cn/models/dengcunqin/matcha_tts_zh_en_20251010/file/view/master/README.md), [sherpa-onnx exact runtime license](https://github.com/k2-fsa/sherpa-onnx/blob/3dc7c569f31ca2cd4a20ed6f7db780327e6714c5/LICENSE), [official Matcha model page and archive contents](https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/matcha-icefall-zh-en.html).

Before product shipment, Core packaging must preserve the exact artifact/source
provenance and assemble the Apache-2.0 and third-party notices for the runtime,
model, Vocos, lexicon/FST/tokens and embedded `espeak-ng-data`. Obtaining fuller
training-data and voice-rights confirmation remains recommended risk reduction,
but it is not required to close Audio M4 or begin Gate 3 under the USER decision.

## 4. Gate decision and close instruction

**Gate 2B technical delivery and all three final references are accepted.**
Silero VAD, whisper.cpp base-Q8 and Matcha zh/en + Vocos 16 kHz are approved for
the stated internal, final-reference, product-integration and redistribution
boundaries. Matcha's incomplete data lineage is an explicit USER-owned Accepted
Risk, while notice completion remains a downstream packaging obligation.

Core Designer approves Audio M4 closure. After Audio receives this response with
its full Core commit SHA, Audio may:

1. record `POC Accepted` / M4 `COMPLETE` and the Matcha Accepted Risk;
2. create the immutable annotated tag `audio_m4` on Audio's exact completion commit; and
3. close `POC-audio-DEL-2026-001-R1`.

This approval authorizes Gate 3 to consume the exact Matcha reference and create
the corresponding product dependency lock. It does not waive Gate 3 technical
acceptance or the redistribution notice-package obligation.
