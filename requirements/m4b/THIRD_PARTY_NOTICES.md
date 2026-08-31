# M4b LiteRT-LM and Gemma third-party notices

The M4b product closure contains the exact, unmodified artifacts identified in
`llm-artifacts.json`. A redistributable package must ship the complete upstream
Apache License 2.0 text, this notice, the pinned source metadata, and any NOTICE
files supplied by upstream. This inventory is not a substitute for the license.

## LiteRT-LM runtime

- Component: `litert-lm-api` 0.16.0 and bundled `liblitert-lm.so`.
- Source: `google-ai-edge/LiteRT-LM` commit
  `924e79c91542761242244e4f1651851f822e4cbb`.
- License: Apache-2.0, as declared by the wheel METADATA and upstream project.
- Required retention: wheel METADATA, source attribution, Apache-2.0 text, and
  any upstream NOTICE file. Core does not modify the wheel or native library.

## Gemma 4 E2B mobile model

- Artifact: `gemma-4-E2B-it.litertlm`, 2,588,147,712 bytes.
- Source: `litert-community/gemma-4-E2B-it-litert-lm` revision
  `6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94`.
- Quantization: artifact-embedded mobile 2/4/8-bit mixture.
- License disposition: Apache-2.0 in the Accepted upstream/model metadata.
- Required retention: pinned model-card/source metadata, author attribution,
  Apache-2.0 text, and any model NOTICE supplied by upstream.

The model bytes, runtime wheel and native binary remain outside Git. Runtime
download, alternate model selection, endpoint fallback and removal of license
metadata are not permitted by the product profile.
