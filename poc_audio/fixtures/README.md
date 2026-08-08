# M1 Fixture Policy

The tracked `catalog.json` starts with deterministic, non-sensitive fake data
for validating harness and schema behaviour. These fixtures are not speech
quality evidence and cannot be used to advance or reject a real VAD, ASR, or
TTS candidate.

Before the M1 frozen gate permits real candidates, the catalog must add:

- licensed or project-authorized VAD/ASR audio with controlled artifact
  location, checksum, duration, language/noise metadata and labels/reference;
- at least the frozen counts and category coverage;
- normalization and scoring versions;
- sensitivity and redistribution policy;
- evidence that private audio, raw PCM and sensitive transcripts remain out of
  Git.

Changing a fixture file changes its checksum and requires gate review once the
catalog is frozen.
