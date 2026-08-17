# Controlled candidate artifacts

This directory is the operator-controlled, non-Git store for candidate source
archives, model/voice files, license notices, and acquisition metadata. Gate 1A
permits downloading, hashing, unpacking, and reading these files solely for
provenance review and the Gate 1B exact candidate proposal.

Before a separate Core Gate 1B candidate-scope ACK, do not build, install,
import, load, or execute any real VAD, ASR, or TTS runtime, model, or voice. Do
not run inference, benchmarks, Pi candidate tests, HAL integration, or User
scoring. Never add artifacts, extracted trees, wheels, native libraries, raw
audio, or private transcripts to Git.

The tracked proposal records sanitized relative locators, upstream URLs,
filenames, sizes, SHA-256 values, licenses/notices, and acquisition timestamps.
The local directory contents are intentionally ignored.
