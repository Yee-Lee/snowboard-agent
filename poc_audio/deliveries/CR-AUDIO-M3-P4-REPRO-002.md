# CR-AUDIO-M3-P4-REPRO-002 — Restore reproducible P4-A10 dependency artifacts

Status: `OPEN — CORE/DESIGNER DECISION REQUIRED`
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
- P4-A10's prior evidence remains traceable, but its current independent replay
  is `INCONCLUSIVE` until matching dependency artifacts or corrected approved
  hashes are supplied.
- Core P4 final selection ACK and the Core Audio real-backend unblock remain
  pending; this request must not be bypassed by treating cached wheels as a
  production dependency selection.

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

