# ADDENDUM-AUDIO-M4-MATCHA-LICENSE-001

- Date: 2026-08-25
- From: Audio POC
- To: Core Designer / Developer / Reviewer
- Status: `APPEND-ONLY LICENSE EVIDENCE CORRECTION / RESPONSE REQUIRED`
- Supersedes: only the Matcha license wording in `DELIVERY-AUDIO-M4-GATE2B-001`
- Original delivery SHA: `b0159b5ae7862d47f1c860ebaaa7108cc0a9876f`
- Corrected Audio delivery SHA: `ca51bce9b4e205d9c9faf004d41c27169f108a3f`

## Correction

The selected Matcha acoustic model does have an explicit published license.
The pinned author ModelScope repository
`dengcunqin/matcha_tts_zh_en_20251010` at commit
`f05803ec98df733d5775dfb0c40a919ae699cfb6` declares
`Apache License 2.0`. Its `model-steps-3.onnx` SHA-256
`524286bf6cf11be74329ae1c682ac69e34d6860c2ea9fd1290319d561540b16a`
matches the tested archive. Vocos SHA-256
`b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e`
also matches the pinned author repository.

The earlier statement must not be interpreted as “Matcha has no model
license.” The archive's lack of an embedded license copy is a notice-packaging
finding, not evidence that no license was granted.

## Remaining decision

The public model card names only unspecified mixed Chinese/English training
data. It does not provide the datasets, source/voice rights, commercial terms
or a complete component notice inventory for lexicon/FST/tokens/espeak data.
Core must therefore acknowledge the Apache-2.0 model grant and decide the
remaining data-lineage and notice-packaging risk. If Core does not accept that
risk, Matcha remains an internal technical reference and a reversible product
no-go pending author clarification or replacement TTS.

The complete audit is committed at:

`poc_audio/evidence/m4/M4-MATCHA-LICENSE-LINEAGE-AUDIT-001.md`

Please base the mandatory Gate 2B response on corrected SHA
`ca51bce9b4e205d9c9faf004d41c27169f108a3f` and include the Core response path,
branch and full committed SHA.
