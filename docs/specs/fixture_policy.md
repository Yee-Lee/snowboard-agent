# AR1 Fixture Policy

Status: `AUTHORITATIVE / FROZEN AT AR1M0`

Audit identity, authorization, sensitivity, category, and prior use before
reuse. Old tuning material is regression data. Untouched material may enter a
holdout only after review. Add only the minimum recordings or annotations needed
to close coverage gaps.

Track manifests, references, checksums, licenses, and controlled locators. Raw
or private audio remains outside Git. Development, adjustment, regression, and
final holdout roles are disjoint and frozen before formal runs. Coverage
includes intents, English entities, code-switch, general zh-TW, duration,
pauses, volume, noise, and speech-end cases.

The AR1M0 audit procedure is frozen in
`asr_r1/manifests/fixture_reuse_audit_plan.json`. Its source rows are audit
inputs only: no development, adjustment, regression, or holdout role is
assigned at AR1M0. Any holdout proposal requires completed identity,
authorization, sensitivity, prior-use, and coverage review followed by User
review before role freeze.

## Collection schedule

- AR1M0 freezes this process and collects no audio.
- AR1M1 audits historical sources before real smoke, freezes one authorized
  approximately three-second PCM smoke fixture, and collects a replacement only
  if no suitable reusable item exists.
- By AR1M1 exit, the coverage matrix is complete and only the minimum authorized
  prerecorded gap fixtures or annotations have been collected and audited.
- Before AR1M2A, User reviews holdout proposals and all four disjoint role
  manifests are frozen. AR1M2 cannot add result-driven fixtures or inspect final
  holdout.
- After AR1M2 freezes pipelines, AR1M3 freezes its prompts and capture method,
  then collects target-microphone qualification sessions. They never enter
  tuning or pipeline selection.

If a formal run exposes a genuine fixture-method or coverage blocker, preserve
the failed evidence and stop that run. Collection or recollection requires a
method revision made before new results, review, a new frozen packet, and a
complete rerun; selective replacement is prohibited.
