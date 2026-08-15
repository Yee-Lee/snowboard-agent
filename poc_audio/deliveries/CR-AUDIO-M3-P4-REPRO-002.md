# CR-AUDIO-M3-P4-REPRO-002 — Restore reproducible P4-A10 dependency artifacts

Status: `CLOSED — OPTION 2 A10 RERUN PASS; CORE FINAL ACK PENDING`
Date: 2026-08-15
Decision owner: Core Team Designer

## Trigger and affected delivery

Existing P4-A10 evidence records a clean Pi source build as `PASS`. During the
2026-08-15 live-session preparation, the two candidate source archives and the
pinned pybind11/libsamplerate source commits all matched their recorded SHA-256
values. However, the currently retrievable `packaging`, `setuptools`, and
`vcs-versioning` artifacts for the manifest's stated versions did not match the
manifest's recorded hashes. Without the retained matching artifacts,
`samplerate` source metadata fell back to `0.0.0` rather than the required
`0.2.4`.

This does not alter the earlier A10 `PASS`, candidate versions, or P4 gates.
It does mean the current controlled environment cannot independently rerun the
full dependency chain from the manifest alone. A Pi cache wheel that identifies
as `samplerate 0.2.4` was used only for the A06–A09 runtime and is recorded as a
non-reference raw evidence artifact.

## Impact

- P4-A06 through A09 are `PASS` at
  `55085162fbcdbb027f0958e945918874e5df6828`.
- P4-A10's current independent replay is `PASS` at
  `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`; reviewed evidence is
  [`P4-A10-RERUN-002`](../evidence/m3_option_a/P4-A10-RERUN-002.md).
- Core P4 final selection ACK and the Core Audio real-backend unblock remain
  pending; this request must not be bypassed by treating cached wheels as a
  production dependency selection.

## Decision received

Core Team Designer accepted Option 2 in
[`RESP-AUDIO-M3-P4-REPRO-002`](../../docs/pm_handoff/RESP-AUDIO-M3-P4-REPRO-002.md):
the POC may replace the four mismatching build-wheel hashes after basic
provenance and license review, then must perform a fresh Pi clean build and
P4-A10 rerun. This approval does not issue the P4 final selection ACK.

The replacement files were checked against the official PyPI release metadata
on 2026-08-15: each is a non-yanked, same-name wheel for the already pinned
version, and each local SHA-256 matches the PyPI SHA-256. Their license
metadata is `MIT`, except `packaging`, which is `Apache-2.0 OR BSD-2-Clause`.
The approved values are recorded in `option_a_candidates.json`; no candidate
package, source archive, native-source commit, or license choice changed.

## Closure evidence

The clean Pi rerun built both candidate sdists with package indexes disabled,
installed the generated wheels into a separate fresh environment, and verified
the pinned package/module identities and native linkage. The first controller
attempt is retained as a `FAIL` caused by an invalid local artifact filename;
the subsequent fresh rerun is `PASS`. P4 evidence is now ready for Core
Designer final selection review, but this closure does not itself grant that
ACK or unblock Core real-backend work.

## Requested decision

Core/Designer should choose one of the following before final P4 disposition:

1. Supply the retained, hash-matching build artifacts and controlled retrieval
   location so the Pi clean build can be repeated.
2. Approve corrected artifact hashes with provenance and license review, then
   require a fresh clean Pi build and A10 rerun.
3. Reject the candidate dependency path and request an evidence-backed
   alternative binding/resampler.

## Recommendation

Use option 1 if the original retained artifacts are available; otherwise use
option 2. Do not issue the P4 final selection ACK until the selected option has
reproduced A10 with a complete artifact chain.
