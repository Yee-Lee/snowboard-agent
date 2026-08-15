# M1 P4-A10 Option 2 clean-build rerun

- **Test ID:** `P4-A10-RERUN-002`
- **Delivery requirement:** `DELIVERY-AUDIO-POC-M3-VALIDATION-001`, P4-A10
- **Decision input:** `RESP-AUDIO-M3-P4-REPRO-002`, Option 2 accepted
- **Purpose:** reproduce the pinned Option A source builds on a clean Pi after
  Core-approved build-wheel hash correction, without a package index

## Preconditions

- The Pi test checkout is the exact, clean 40-character POC SHA for this
  packet and `environment_pre_test.sh` has passed.
- The controlled, Git-ignored artifact directory contains exactly one checked
  NumPy 2.4.2 cp313 aarch64 wheel; the two candidate sdists; the five pinned
  build wheels; and the two pinned CMake dependency source archives.
- Each artifact SHA-256 matches `option_a_candidates.json`. The updated four
  build-wheel hashes have basic provenance/license review recorded in
  `CR-AUDIO-M3-P4-REPRO-002`.
- Pi system versions remain those pinned by the candidate manifest: Python
  3.13.5, CMake 3.31.6, GCC/G++ 14.2.0, and the existing ALSA development
  package. No audio device is opened for this test.

## Command

```sh
bash poc_audio/tools/run_option_a_a10_clean_build.sh \
  --artifact-dir /controlled/p4-a10-artifacts \
  --output poc_audio/evidence/m3_option_a/<timestamp>/raw/a10-clean-build
```

## Frozen pass condition

`PASS` requires the runner to verify all inputs, build `pyalsaaudio==0.11.0`
and `samplerate==0.2.4` from source with package indexes disabled, install the
generated wheels into a separate new virtual environment, and record matching
distribution/module identities plus native-library identity. The generated
wheels remain raw evidence artifacts, not Core reference deliverables.

Any unavailable pinned system tool, checksum mismatch, source-build failure,
identity mismatch, or incomplete raw record is `FAIL` or `INCONCLUSIVE` after
evidence review; it does not authorize a P4 final selection ACK.
